-- ПР №1, самостоятельное задание 2. Скрипты каталога /docker-entrypoint-initdb.d выполняются официальным
-- образом PostgreSQL по алфавиту и только при первом запуске контейнера, пока том данных пуст.
CREATE TABLE student_groups (
    id         serial PRIMARY KEY,
    name       varchar(20)  NOT NULL UNIQUE,
    specialty  varchar(100) NOT NULL
);

CREATE TABLE students (
    id           serial PRIMARY KEY,
    group_id     integer      NOT NULL REFERENCES student_groups (id),
    card_number  varchar(10)  NOT NULL UNIQUE,
    full_name    varchar(150) NOT NULL,
    email        varchar(100)
);

CREATE TABLE lecture_visits (
    student_id  integer NOT NULL REFERENCES students (id),
    visit_date  date    NOT NULL,
    is_present  boolean NOT NULL,
    PRIMARY KEY (student_id, visit_date)
);

COMMENT ON TABLE lecture_visits IS 'Отметки посещения лекций (тестовые данные скрипта инициализации)';
