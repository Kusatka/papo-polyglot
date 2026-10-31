-- ПР №1, самостоятельное задание 2: тестовые данные (выполняется после 01_schema.sql).
INSERT INTO student_groups (name, specialty) VALUES
    ('БСБО-01-23', '38.03.05 Бизнес-информатика'),
    ('ИКБО-01-23', '09.03.04 Программная инженерия');

INSERT INTO students (group_id, card_number, full_name, email) VALUES
    (1, '23Б0101', 'Андреев Илья Сергеевич',     '23b0101@edu.mirea.ru'),
    (1, '23Б0102', 'Беляев Даниил Олегович',     '23b0102@edu.mirea.ru'),
    (1, '23Б0103', 'Васильева Анна Игоревна',    '23b0103@edu.mirea.ru'),
    (2, '23Б0301', 'Богданов Алексей Олегович',  '23b0301@edu.mirea.ru'),
    (2, '23Б0302', 'Григорьева Мария Павловна',  '23b0302@edu.mirea.ru');

-- по одной отметке на каждую из трёх недель февраля, посещение — детерминированно по номеру студента
INSERT INTO lecture_visits (student_id, visit_date, is_present)
SELECT s.id, d::date, (s.id + extract(day FROM d)::int) % 3 <> 0
FROM students s, generate_series(date '2026-02-09', date '2026-02-23', interval '7 days') AS d;
