-- Справочник студентов и расписание (минимальный набор для журнала посещений)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_card_number VARCHAR(20) NOT NULL UNIQUE,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    patronymic VARCHAR(100),
    group_name VARCHAR(50) NOT NULL
);

CREATE TABLE schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_name VARCHAR(50) NOT NULL,
    course_name VARCHAR(500) NOT NULL,
    lecture_number INT NOT NULL,
    scheduled_date DATE NOT NULL,
    week_start_date DATE NOT NULL,       -- понедельник недели = ключ партиционирования журнала
    classroom VARCHAR(50),
    teacher_name VARCHAR(300)
);

-- Журнал посещений лекций, партиционированный по неделе посещения (RANGE по понедельнику недели)
CREATE TABLE attendance (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL,
    student_id UUID NOT NULL,
    week_start_date DATE NOT NULL,
    is_present BOOLEAN NOT NULL DEFAULT FALSE,
    marked_at TIMESTAMP DEFAULT NOW(),
    note VARCHAR(500),
    PRIMARY KEY (id, week_start_date)    -- ключ партиционирования обязан входить в первичный ключ
) PARTITION BY RANGE (week_start_date);

CREATE UNIQUE INDEX uq_attendance_schedule_student ON attendance (schedule_id, student_id, week_start_date);
CREATE INDEX idx_attendance_student ON attendance (student_id);

-- Партиции на N недель вперёд: attendance_wГГГГ_ММ_ДД = [понедельник, следующий понедельник)
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

SELECT create_weekly_partitions('2026-02-09', 20);          -- весенний семестр 2026: 20 недель
CREATE TABLE attendance_default PARTITION OF attendance DEFAULT;   -- даты вне семестра
