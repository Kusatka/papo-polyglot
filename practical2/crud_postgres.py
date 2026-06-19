"""
Практическая №2 — CRUD в PostgreSQL (транзакционные данные + партиционирование).
Данные: посещение лекций студентами, партиционирование ПО НЕДЕЛЕ посещения.
Данные заполняются случайным выбором (random).
Цикл: создать (партиционированную) таблицу → добавить → прочитать по ключу →
      изменить → удалить запись → удалить таблицу.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

DDL = """
DROP TABLE IF EXISTS p2_attendance CASCADE;
CREATE TABLE p2_attendance (
    student_id INT  NOT NULL,
    lecture_id INT  NOT NULL,
    visit_date DATE NOT NULL,
    attended   BOOLEAN NOT NULL,
    PRIMARY KEY (student_id, lecture_id, visit_date)
) PARTITION BY RANGE (visit_date);
"""


def demo(conn=None) -> list[str]:
    own = False
    if conn is None:
        from common.connections import pg_connect
        conn = pg_connect(autocommit=True); own = True
    log: list[str] = []
    rnd = random.Random(2023)
    try:
        cur = conn.cursor()
        cur.execute("SET client_min_messages TO warning")

        # 1. Создать партиционированную таблицу + недельные партиции
        cur.execute(DDL)
        base = date(2025, 9, 1)            # понедельник
        for w in range(4):                 # 4 недельные партиции
            ws = base + timedelta(weeks=w)
            we = ws + timedelta(days=7)
            cur.execute(f"CREATE TABLE p2_attendance_w{w+1} PARTITION OF p2_attendance "
                        f"FOR VALUES FROM ('{ws}') TO ('{we}')")
        log.append("1. Создана таблица p2_attendance (PARTITION BY RANGE недели) + 4 партиции")

        # 2. Добавить данные случайным выбором
        rows = []
        for student_id in range(1, 6):
            for w in range(4):
                d = base + timedelta(weeks=w, days=rnd.randint(0, 4))
                rows.append((student_id, 100 + w, d, rnd.random() < 0.7))
        cur.executemany("INSERT INTO p2_attendance VALUES (%s,%s,%s,%s)", rows)
        log.append(f"2. Случайно сгенерировано и вставлено строк: {len(rows)}")

        # 3. Прочитать по ключу + показать раскладку по партициям
        cur.execute("SELECT attended FROM p2_attendance WHERE student_id=1 AND lecture_id=100")
        log.append(f"3. Чтение по ключу (student=1, lecture=100): attended={cur.fetchone()[0]}")
        cur.execute("SELECT tableoid::regclass::text, count(*) FROM p2_attendance "
                    "GROUP BY 1 ORDER BY 1")
        log.append("   раскладка по партициям: " +
                   ", ".join(f"{p}={c}" for p, c in cur.fetchall()))

        # 4. Изменить
        cur.execute("UPDATE p2_attendance SET attended=true WHERE student_id=1 AND lecture_id=100")
        log.append("4. Обновление: (student=1, lecture=100).attended=true")

        # 5. Удалить запись
        cur.execute("DELETE FROM p2_attendance WHERE student_id=1 AND lecture_id=100")
        cur.execute("SELECT count(*) FROM p2_attendance")
        log.append(f"5. Запись удалена; всего строк: {cur.fetchone()[0]}")

        # 6. Удалить хранилище (таблицу со всеми партициями)
        cur.execute("DROP TABLE p2_attendance CASCADE")
        log.append("6. Таблица p2_attendance удалена (со всеми партициями)")
    finally:
        if own:
            conn.close()
    return log


if __name__ == "__main__":
    print("\n".join(demo()))
