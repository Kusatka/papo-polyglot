"""
Лаб. №1 — федеративный запрос: 10 студентов с минимальным процентом
посещения лекций, содержащих заданный термин/фразу, за период.

Маршрут извлечения (обоснование — в отчёте):
  1) ElasticSearch  — найти лекции, чьё содержание содержит термин/фразу
                      (инвертированный индекс, русский анализатор, match_phrase).
  2) PostgreSQL     — по найденным лекциям и периоду посчитать % посещения
                      на студента (агрегат над партиционированной по неделям
                      таблицей attendance → partition pruning по visit_date).
  3) Redis          — обогатить топ-10 «полной информацией о студенте»
                      (точечный доступ по ключу = номер зачётной книжки).

Клиенты передаются параметрами (внедрение зависимостей) — это упрощает
замену реализации хранилища и автономную проверку функций.
"""
from __future__ import annotations

from datagen.generate import LECTURES_INDEX


def search_lectures_by_term(es, term: str, date_from: str | None = None,
                            date_to: str | None = None, academic_year: str | None = None,
                            size: int = 3000) -> list[dict]:
    """Шаг 1. Возвращает [{lecture_id, course_id, course_code, course_title}]."""
    term = term.strip()
    is_phrase = " " in term
    if is_phrase:
        text_q = {"match_phrase": {"content": {"query": term}}}
    else:
        text_q = {"multi_match": {"query": term,
                                  "fields": ["content", "topic^2", "course_title"]}}
    filters: list[dict] = []
    if date_from or date_to:
        rng: dict = {}
        if date_from:
            rng["gte"] = date_from
        if date_to:
            rng["lte"] = date_to
        filters.append({"range": {"planned_date": rng}})
    if academic_year:
        filters.append({"term": {"academic_year": academic_year}})

    query = {"bool": {"must": [text_q], "filter": filters}}
    res = es.search(index=LECTURES_INDEX, query=query, size=size,
                    source=["lecture_id", "course_id", "course_code", "course_title"])
    return [h["_source"] for h in res["hits"]["hits"]]


ATTENDANCE_SQL = """
SELECT s.student_id, s.record_book_no, s.last_name, s.first_name, s.middle_name,
       g.code AS group_code,
       count(*) FILTER (WHERE a.attended) AS attended,
       count(*)                            AS total,
       round(100.0 * count(*) FILTER (WHERE a.attended) / NULLIF(count(*), 0), 1) AS percent
FROM attendance a
JOIN student s     ON s.student_id = a.student_id
JOIN study_group g ON g.group_id   = s.group_id
WHERE a.lecture_id = ANY(%(lecture_ids)s)
  AND a.visit_date BETWEEN %(date_from)s AND %(date_to)s
GROUP BY s.student_id, s.record_book_no, s.last_name, s.first_name, s.middle_name, g.code
HAVING count(*) > 0
ORDER BY percent ASC, attended ASC, s.record_book_no
LIMIT %(limit)s
"""


def attendance_percent(conn, lecture_ids: list[int], date_from: str, date_to: str,
                       limit: int = 10) -> list[dict]:
    """Шаг 2. Процент посещения по студентам (минимальные — первыми)."""
    cur = conn.cursor()
    cur.execute(ATTENDANCE_SQL, {"lecture_ids": lecture_ids, "date_from": date_from,
                                 "date_to": date_to, "limit": limit})
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def enrich_from_redis(r, record_book_no: str) -> dict:
    """Шаг 3. Полная карточка студента из Redis (ключ = зачётка)."""
    data = r.hgetall(f"student:{record_book_no}")
    return data or {}


def run(es, pg_conn, redis, *, term: str, date_from: str, date_to: str,
        academic_year: str | None = None, limit: int = 10) -> dict:
    """Полный федеративный запрос лаб. №1."""
    lectures = search_lectures_by_term(es, term, date_from, date_to, academic_year)
    lecture_ids = sorted({l["lecture_id"] for l in lectures})
    course_ids = sorted({l["course_id"] for l in lectures})

    students_out: list[dict] = []
    rows = attendance_percent(pg_conn, lecture_ids, date_from, date_to, limit) if lecture_ids else []
    for row in rows:
        card = enrich_from_redis(redis, row["record_book_no"])
        fio = card.get("fio") or " ".join(
            x for x in [row["last_name"], row["first_name"], row["middle_name"]] if x)
        students_out.append({
            "record_book_no": row["record_book_no"],
            "fio": fio,
            "last_name": row["last_name"], "first_name": row["first_name"],
            "middle_name": row["middle_name"],
            "group": card.get("group") or row["group_code"],
            "specialty": card.get("specialty"),
            "email": card.get("email"),
            "birth_date": card.get("birth_date"),
            "attendance_percent": float(row["percent"]) if row["percent"] is not None else None,
            "attended": int(row["attended"]), "total": int(row["total"]),
        })
    return {
        "term": term,
        "period": {"from": date_from, "to": date_to},
        "academic_year": academic_year,
        "matched_lectures": len(lecture_ids),
        "matched_courses": course_ids,
        "count": len(students_out),
        "students": students_out,
    }
