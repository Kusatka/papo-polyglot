-- =====================================================================================
-- ПР №3. Физическая модель PostgreSQL — основное хранилище (источник истины) системы
-- управления учебным процессом. База: university_system.
-- Основа — схема методических указаний; расширения помечены «РАСШИРЕНИЕ» и нужны
-- аналитическим запросам лабораторных работ №1–3 (термины, техника, теги, курсы по выбору).
-- =====================================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID как первичные ключи: один id во всех хранилищах
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- нечёткий поиск по ФИО (триграммы)

-- ---------- Организационная структура -----------------------------------------------
CREATE TABLE universities (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name         VARCHAR(500) NOT NULL,           -- «МИРЭА — Российский технологический университет»
    short_name   VARCHAR(100),                    -- «РТУ МИРЭА»
    address      TEXT,
    website      VARCHAR(255),
    founded_year INT,
    created_at   TIMESTAMP DEFAULT NOW(),         -- created_at / updated_at нужны CDC (ЛР №4–6)
    updated_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE institutes (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    university_id UUID NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    name          VARCHAR(500) NOT NULL,
    short_name    VARCHAR(100),                   -- «ИКБ», «ИИТ»
    dean          VARCHAR(300),                   -- директор института
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_institutes_university ON institutes(university_id);

CREATE TABLE departments (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institute_id UUID NOT NULL REFERENCES institutes(id) ON DELETE CASCADE,
    name         VARCHAR(500) NOT NULL,
    short_name   VARCHAR(100),                    -- «КИС», «КПИ»
    head         VARCHAR(300),                    -- заведующий кафедрой
    room         VARCHAR(50),
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_departments_institute ON departments(institute_id);

CREATE TABLE specialties (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name           VARCHAR(500) NOT NULL,
    code           VARCHAR(20) NOT NULL,          -- «38.03.05»
    degree_level   VARCHAR(20) NOT NULL CHECK (degree_level IN ('bachelor', 'master', 'specialist')),
    duration_years INT NOT NULL DEFAULT 4,
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_specialties_code ON specialties(code);

-- Кафедра <-> специальность (M:N): специальность может вестись несколькими кафедрами
CREATE TABLE department_specialties (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    specialty_id  UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    is_primary    BOOLEAN DEFAULT FALSE,          -- выпускающая кафедра
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (department_id, specialty_id)
);
CREATE INDEX idx_dept_spec_department ON department_specialties(department_id);
CREATE INDEX idx_dept_spec_specialty  ON department_specialties(specialty_id);

-- ---------- Учебный процесс -----------------------------------------------------------
CREATE TABLE lecture_courses (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specialty_id   UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    department_id  UUID REFERENCES departments(id) ON DELETE SET NULL,  -- РАСШИРЕНИЕ: кафедра, ведущая курс
    name           VARCHAR(500) NOT NULL,
    description    TEXT,
    semester       INT NOT NULL CHECK (semester BETWEEN 1 AND 12),
    total_hours    INT NOT NULL,
    lecture_hours  INT DEFAULT 0,
    practice_hours INT DEFAULT 0,
    lab_hours      INT DEFAULT 0,
    is_elective    BOOLEAN NOT NULL DEFAULT FALSE,                      -- РАСШИРЕНИЕ: курс по выбору
    tags           TEXT[] NOT NULL DEFAULT '{}',                        -- РАСШИРЕНИЕ: «спецдисциплина кафедры» и др.
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (specialty_id, name, semester)
);
CREATE INDEX idx_courses_specialty  ON lecture_courses(specialty_id);
CREATE INDEX idx_courses_department ON lecture_courses(department_id);
CREATE INDEX idx_courses_tags       ON lecture_courses USING GIN (tags);

-- Занятие курса: лекция, практика или лабораторная
CREATE TABLE lectures (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id         UUID NOT NULL REFERENCES lecture_courses(id) ON DELETE CASCADE,
    title             VARCHAR(500) NOT NULL,
    annotation        TEXT,
    lecture_type      VARCHAR(20) NOT NULL CHECK (lecture_type IN ('lecture', 'practice', 'lab')),
    order_number      INT NOT NULL,
    duration_minutes  INT DEFAULT 90,
    tech_requirements TEXT,                       -- РАСШИРЕНИЕ: требования к техническим средствам (ЛР №2)
    tags              TEXT[] NOT NULL DEFAULT '{}', -- РАСШИРЕНИЕ: темы и тег спецдисциплины (ЛР №3)
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW(),
    UNIQUE (course_id, order_number)
);
CREATE INDEX idx_lectures_course ON lectures(course_id);
CREATE INDEX idx_lectures_type   ON lectures(lecture_type);
CREATE INDEX idx_lectures_tags   ON lectures USING GIN (tags);

-- Материалы занятия (нормализованно: одна строка — один материал). Дубль-агрегат — в MongoDB
CREATE TABLE lecture_materials (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lecture_id   UUID NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL
                 CHECK (content_type IN ('text', 'presentation', 'pdf', 'video_link', 'code_sample', 'exercise')),
    title        VARCHAR(500),
    content_text TEXT,
    file_url     VARCHAR(1000),
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_materials_lecture ON lecture_materials(lecture_id);
CREATE INDEX idx_materials_type    ON lecture_materials(content_type);

-- ---------- Группы и студенты ---------------------------------------------------------
CREATE TABLE student_groups (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specialty_id    UUID NOT NULL REFERENCES specialties(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL UNIQUE,  -- «БСБО-01-23»
    enrollment_year INT NOT NULL,
    curator         VARCHAR(300),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_groups_specialty ON student_groups(specialty_id);

CREATE TABLE students (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id            UUID NOT NULL REFERENCES student_groups(id) ON DELETE CASCADE,
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    patronymic          VARCHAR(100),
    email               VARCHAR(255) UNIQUE,
    phone               VARCHAR(20),
    student_card_number VARCHAR(20) UNIQUE,       -- номер студенческого билета / зачётной книжки
    enrollment_date     DATE NOT NULL,
    status              VARCHAR(20) DEFAULT 'active'
                        CHECK (status IN ('active', 'academic_leave', 'expelled', 'graduated')),
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_students_group  ON students(group_id);
CREATE INDEX idx_students_name   ON students(last_name, first_name);
CREATE INDEX idx_students_status ON students(status);
CREATE INDEX idx_students_fio_trgm ON students USING GIN ((last_name || ' ' || first_name) gin_trgm_ops);

-- РАСШИРЕНИЕ: выбор курсов по выбору (M:N студент <-> курс). Обязательные курсы группа
-- слушает целиком (по специальности и семестру), выборные — только записавшиеся студенты
CREATE TABLE student_electives (
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id  UUID NOT NULL REFERENCES lecture_courses(id) ON DELETE CASCADE,
    chosen_at  TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (student_id, course_id)
);
CREATE INDEX idx_electives_course ON student_electives(course_id);

-- ---------- Расписание и журнал посещений ---------------------------------------------
CREATE TABLE schedule (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lecture_id      UUID NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    group_id        UUID NOT NULL REFERENCES student_groups(id) ON DELETE CASCADE,
    scheduled_date  DATE NOT NULL,
    week_start_date DATE NOT NULL,                -- понедельник недели (денормализовано: ключ партиций attendance)
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    classroom       VARCHAR(50),
    teacher_name    VARCHAR(300),
    status          VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    CHECK (week_start_date = date_trunc('week', scheduled_date)::date)
);
CREATE INDEX idx_schedule_date       ON schedule(scheduled_date);
CREATE INDEX idx_schedule_week       ON schedule(week_start_date);
CREATE INDEX idx_schedule_group      ON schedule(group_id);
CREATE INDEX idx_schedule_lecture    ON schedule(lecture_id);
CREATE INDEX idx_schedule_group_date ON schedule(group_id, scheduled_date);

-- Журнал посещений — самая быстрорастущая таблица, секционирована по неделям (RANGE).
-- Внешние ключи не объявлены (как в методических указаниях): массовая вставка быстрее,
-- партиции свободно отсоединяются и переносятся; целостность обеспечивает приложение.
CREATE TABLE attendance (
    id              UUID NOT NULL DEFAULT uuid_generate_v4(),
    schedule_id     UUID NOT NULL,
    student_id      UUID NOT NULL,
    week_start_date DATE NOT NULL,                -- ключ партиционирования
    is_present      BOOLEAN NOT NULL DEFAULT FALSE,
    marked_at       TIMESTAMP DEFAULT NOW(),
    marked_by       VARCHAR(300),
    note            VARCHAR(500),
    created_at      TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id, week_start_date)             -- PK обязан включать ключ партиционирования
) PARTITION BY RANGE (week_start_date);
CREATE UNIQUE INDEX uq_attendance_schedule_student ON attendance(schedule_id, student_id, week_start_date);
CREATE INDEX idx_attendance_student ON attendance(student_id);
CREATE INDEX idx_attendance_present ON attendance(is_present);

CREATE OR REPLACE FUNCTION create_weekly_partitions(start_date DATE, num_weeks INT) RETURNS VOID AS $$
DECLARE
    week_start DATE := date_trunc('week', start_date)::DATE;
    part TEXT;
BEGIN
    FOR i IN 0..num_weeks - 1 LOOP
        part := 'attendance_w' || to_char(week_start, 'YYYY_MM_DD');
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = part) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF attendance FOR VALUES FROM (%L) TO (%L)',
                           part, week_start, week_start + 7);
        END IF;
        week_start := week_start + 7;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT create_weekly_partitions('2026-02-09', 20);                -- весенний семестр 2026
CREATE TABLE attendance_default PARTITION OF attendance DEFAULT;   -- даты вне семестра

-- ---------- Представления -------------------------------------------------------------
CREATE VIEW v_full_schedule AS
SELECT s.id AS schedule_id, s.scheduled_date, s.week_start_date, s.start_time, s.end_time, s.classroom,
       s.teacher_name, s.status AS schedule_status,
       l.id AS lecture_id, l.title AS lecture_title, l.lecture_type, l.tech_requirements,
       lc.id AS course_id, lc.name AS course_name, lc.semester,
       sg.id AS group_id, sg.name AS group_name,
       sp.name AS specialty_name, sp.code AS specialty_code,
       d.short_name AS department, i.short_name AS institute, u.short_name AS university
FROM schedule s
JOIN lectures l ON s.lecture_id = l.id
JOIN lecture_courses lc ON l.course_id = lc.id
JOIN specialties sp ON lc.specialty_id = sp.id
JOIN department_specialties ds ON sp.id = ds.specialty_id AND ds.is_primary
JOIN departments d ON ds.department_id = d.id
JOIN institutes i ON d.institute_id = i.id
JOIN universities u ON i.university_id = u.id
JOIN student_groups sg ON s.group_id = sg.id;

CREATE VIEW v_student_attendance_stats AS
SELECT st.id AS student_id, st.student_card_number, st.last_name || ' ' || st.first_name AS student_name,
       sg.name AS group_name,
       COUNT(a.id) AS total_classes,
       COUNT(*) FILTER (WHERE a.is_present) AS attended,
       COUNT(*) FILTER (WHERE NOT a.is_present) AS missed,
       ROUND(COUNT(*) FILTER (WHERE a.is_present)::NUMERIC / NULLIF(COUNT(a.id), 0) * 100, 1) AS attendance_percentage
FROM students st
JOIN student_groups sg ON st.group_id = sg.id
LEFT JOIN attendance a ON a.student_id = st.id
GROUP BY st.id, st.student_card_number, st.last_name, st.first_name, sg.name;

-- РАСШИРЕНИЕ: кто слушает курс — вся группа для обязательного курса, записавшиеся — для курса по выбору
CREATE VIEW v_course_listeners AS
SELECT lc.id AS course_id, lc.name AS course_name, lc.semester, st.id AS student_id, sg.name AS group_name
FROM lecture_courses lc
JOIN student_groups sg ON sg.specialty_id = lc.specialty_id
JOIN students st ON st.group_id = sg.id
WHERE NOT lc.is_elective
   OR EXISTS (SELECT 1 FROM student_electives e WHERE e.student_id = st.id AND e.course_id = lc.id);
