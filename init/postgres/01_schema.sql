-- ============================================================================
--  Практическая работа №3 — каноническая реляционная схема (источник истины)
--
--  Предметная область: кафедра, специальности, учебные группы, студенты,
--  курсы (дисциплины), лекции, запись на курсы (вкл. курсы по выбору) и
--  посещаемость лекций. Эта схема в PostgreSQL — единый источник истины;
--  из неё данные проецируются в остальные четыре хранилища (Redis, MongoDB,
--  Neo4j, ElasticSearch) — см. practical3/polyglot_mapping.md.
--
--  Ключевой элемент: таблица attendance партиционирована ПО НЕДЕЛЕ посещения
--  (PARTITION BY RANGE (visit_date), по одной партиции на ISO-неделю).
--  Скрипт идемпотентен (IF NOT EXISTS / CREATE OR REPLACE).
-- ============================================================================

-- ── 1. Кафедра ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS department (
    department_id  SERIAL PRIMARY KEY,
    code           VARCHAR(16)  NOT NULL UNIQUE,
    name           VARCHAR(200) NOT NULL
);

-- ── 2. Специальность / направление подготовки ──────────────────────
CREATE TABLE IF NOT EXISTS specialty (
    specialty_id   SERIAL PRIMARY KEY,
    code           VARCHAR(16)  NOT NULL UNIQUE,   -- напр. 38.03.05
    name           VARCHAR(200) NOT NULL,          -- напр. Бизнес-информатика
    department_id  INT NOT NULL REFERENCES department(department_id)
);

-- ── 3. Учебная группа ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS study_group (
    group_id       SERIAL PRIMARY KEY,
    code           VARCHAR(32)  NOT NULL UNIQUE,    -- напр. БСБО-01-23
    specialty_id   INT NOT NULL REFERENCES specialty(specialty_id),
    year_enrolled  SMALLINT NOT NULL
);

-- ── 4. Студент (ключ Redis = record_book_no, номер зачётной книжки) ──
CREATE TABLE IF NOT EXISTS student (
    student_id      SERIAL PRIMARY KEY,
    record_book_no  VARCHAR(16)  NOT NULL UNIQUE,   -- номер зачётки
    last_name       VARCHAR(80)  NOT NULL,
    first_name      VARCHAR(80)  NOT NULL,
    middle_name     VARCHAR(80),
    group_id        INT NOT NULL REFERENCES study_group(group_id),
    email           VARCHAR(160),
    birth_date      DATE
);
CREATE INDEX IF NOT EXISTS ix_student_group ON student(group_id);

-- ── 5. Курс (дисциплина). description -> полнотекст в ElasticSearch ──
CREATE TABLE IF NOT EXISTS course (
    course_id      SERIAL PRIMARY KEY,
    code           VARCHAR(32)  NOT NULL UNIQUE,
    title          VARCHAR(200) NOT NULL,
    description    TEXT,                            -- полнотекстовое описание
    department_id  INT NOT NULL REFERENCES department(department_id),
    study_year     SMALLINT NOT NULL,               -- курс обучения 1..4
    semester       SMALLINT NOT NULL,               -- семестр в году 1..2
    academic_year  VARCHAR(9) NOT NULL,             -- напр. 2025/2026
    is_elective    BOOLEAN NOT NULL DEFAULT FALSE    -- курс по выбору
);
CREATE INDEX IF NOT EXISTS ix_course_dept ON course(department_id);
CREATE INDEX IF NOT EXISTS ix_course_period ON course(study_year, semester, academic_year);

-- ── 6. Теги дисциплин (в т.ч. «специальная дисциплина кафедры») ──────
CREATE TABLE IF NOT EXISTS tag (
    tag_id  SERIAL PRIMARY KEY,
    name    VARCHAR(80) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS course_tag (
    course_id INT NOT NULL REFERENCES course(course_id) ON DELETE CASCADE,
    tag_id    INT NOT NULL REFERENCES tag(tag_id) ON DELETE CASCADE,
    PRIMARY KEY (course_id, tag_id)
);

-- ── 7. Лекция. content -> полнотекст в ES; tech_requirements -> лаб.2 ─
CREATE TABLE IF NOT EXISTS lecture (
    lecture_id          SERIAL PRIMARY KEY,
    course_id           INT NOT NULL REFERENCES course(course_id) ON DELETE CASCADE,
    seq_no              SMALLINT NOT NULL,           -- № лекции в курсе
    topic               VARCHAR(300) NOT NULL,
    content             TEXT,                        -- полнотекст (поиск термина)
    planned_date        DATE NOT NULL,               -- дата проведения
    duration_acad_hours SMALLINT NOT NULL DEFAULT 2, -- 1 лекция = 2 ак. часа
    tech_requirements   TEXT,                        -- требования к тех. средствам
    UNIQUE (course_id, seq_no)
);
CREATE INDEX IF NOT EXISTS ix_lecture_course ON lecture(course_id);
CREATE INDEX IF NOT EXISTS ix_lecture_date ON lecture(planned_date);

-- ── 8. Запись студента на курс (включая курсы по выбору) ─────────────
CREATE TABLE IF NOT EXISTS enrollment (
    enrollment_id  SERIAL PRIMARY KEY,
    student_id     INT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    course_id      INT NOT NULL REFERENCES course(course_id) ON DELETE CASCADE,
    is_elective    BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (student_id, course_id)
);
CREATE INDEX IF NOT EXISTS ix_enrollment_course ON enrollment(course_id);
CREATE INDEX IF NOT EXISTS ix_enrollment_student ON enrollment(student_id);

-- ── 9. Посещаемость — ПАРТИЦИОНИРОВАНА ПО НЕДЕЛЕ (RANGE по visit_date) ─
--     Партиционный ключ visit_date обязан входить в первичный ключ.
CREATE TABLE IF NOT EXISTS attendance (
    student_id  INT      NOT NULL REFERENCES student(student_id)  ON DELETE CASCADE,
    lecture_id  INT      NOT NULL REFERENCES lecture(lecture_id)  ON DELETE CASCADE,
    course_id   INT      NOT NULL REFERENCES course(course_id)    ON DELETE CASCADE,
    visit_date  DATE     NOT NULL,                 -- дата проведения лекции
    iso_year    SMALLINT NOT NULL,                 -- ISO-год недели
    iso_week    SMALLINT NOT NULL,                 -- ISO-номер недели (1..53)
    attended    BOOLEAN  NOT NULL,                 -- присутствовал / нет
    PRIMARY KEY (student_id, lecture_id, visit_date)
) PARTITION BY RANGE (visit_date);

-- Индексы на родителе автоматически наследуются всеми партициями
CREATE INDEX IF NOT EXISTS ix_att_course_date ON attendance(course_id, visit_date);
CREATE INDEX IF NOT EXISTS ix_att_student     ON attendance(student_id);
CREATE INDEX IF NOT EXISTS ix_att_lecture     ON attendance(lecture_id);

-- Партиция по умолчанию — страховка для дат вне созданных недельных партиций
CREATE TABLE IF NOT EXISTS attendance_default PARTITION OF attendance DEFAULT;

-- ── Функция авто-создания недельных партиций (понедельник..воскресенье) ─
-- Создаёт по одной партиции на каждую ISO-неделю в диапазоне [p_start, p_end].
CREATE OR REPLACE FUNCTION create_week_partitions(p_start DATE, p_end DATE)
RETURNS INT AS $$
DECLARE
    w_start DATE := date_trunc('week', p_start)::date;  -- ближайший понедельник
    w_end   DATE;
    pname   TEXT;
    created INT := 0;
BEGIN
    WHILE w_start <= p_end LOOP
        w_end := w_start + INTERVAL '7 days';
        pname := format('attendance_%sw%s',
                        to_char(w_start, 'IYYY'), to_char(w_start, 'IW'));
        IF to_regclass('public.' || pname) IS NULL THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF attendance FOR VALUES FROM (%L) TO (%L)',
                pname, w_start, w_end);
            created := created + 1;
        END IF;
        w_start := w_end;
    END LOOP;
    RETURN created;
END;
$$ LANGUAGE plpgsql;

-- ── Представление: число слушателей курса (для лаб. №2) ─────────────
CREATE OR REPLACE VIEW v_course_listeners AS
    SELECT course_id, COUNT(*)::int AS listeners
    FROM enrollment
    GROUP BY course_id;
