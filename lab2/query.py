"""
Лаб. №2 — федеративный запрос: необходимый объём аудитории для проведения
занятий по курсу заданного СЕМЕСТРА и ГОДА ОБУЧЕНИЯ (курс 1–4), с учётом
требований к техническим средствам. Результат: полная информация о курсе,
лекциях и числе слушателей (= требуемая вместимость аудитории).

Маршрут извлечения (обоснование — в отчёте):
  1) ElasticSearch — отобрать лекции по году обучения (study_year), семестру и
                     учебному году (фильтры-метаданные) и, при необходимости, по
                     требованиям к тех. средствам (полнотекст по tech_requirements).
  2) Neo4j         — число слушателей курса обходом графа
                     (:Course)<-[:ENROLLED]-(:Student). PostgreSQL — резерв.
  3) PostgreSQL    — обогащение полной информацией о курсе (описание дисциплины)
                     из канонического источника истины.
"""
from __future__ import annotations

from datagen.generate import LECTURES_INDEX


def search_course_lectures(es, academic_year: str, study_year: int | None = None,
                           semester: int | None = None, tech_term: str | None = None,
                           course_code: str | None = None, size: int = 5000) -> list[dict]:
    """Шаг 1. Отбор лекций по метаданным (курс/семестр/год) и тех. требованиям."""
    filters: list[dict] = [{"term": {"academic_year": academic_year}}]
    if study_year is not None:                       # «год обучения» = курс 1–4
        filters.append({"term": {"study_year": study_year}})
    if semester is not None:
        filters.append({"term": {"semester": semester}})
    if course_code:
        filters.append({"term": {"course_code": course_code}})
    must: list[dict] = []
    if tech_term and tech_term.strip():
        key = "match_phrase" if " " in tech_term.strip() else "match"
        must.append({key: {"tech_requirements": tech_term}})
    else:
        must.append({"match_all": {}})
    query = {"bool": {"must": must, "filter": filters}}
    res = es.search(index=LECTURES_INDEX, query=query, size=size,
                    source=["lecture_id", "course_id", "course_code", "course_title",
                            "study_year", "semester", "academic_year", "seq_no",
                            "topic", "tech_requirements", "planned_date"])
    return [h["_source"] for h in res["hits"]["hits"]]


def course_listeners_neo4j(driver, course_ids: list[int]) -> dict[int, int]:
    """Шаг 2 (основной). Число слушателей курса обходом графа ENROLLED."""
    cypher = ("UNWIND $ids AS cid "
              "MATCH (c:Course {course_id: cid})<-[:ENROLLED]-(s:Student) "
              "RETURN cid AS course_id, count(s) AS listeners")
    with driver.session() as ses:
        return {r["course_id"]: r["listeners"] for r in ses.run(cypher, ids=course_ids)}


def course_listeners_pg(conn, course_ids: list[int]) -> dict[int, int]:
    """Шаг 2 (резерв). Число слушателей = число записей на курс (enrollment)."""
    cur = conn.cursor()
    cur.execute("SELECT course_id, count(*) FROM enrollment "
                "WHERE course_id = ANY(%s) GROUP BY course_id", (course_ids,))
    return {row[0]: row[1] for row in cur.fetchall()}


def course_details_pg(conn, course_ids: list[int]) -> dict[int, dict]:
    """Шаг 3. Полная информация о курсе (описание дисциплины) из источника истины."""
    cur = conn.cursor()
    cur.execute("SELECT course_id, code, title, description, study_year, semester, "
                "academic_year, is_elective FROM course WHERE course_id = ANY(%s)",
                (course_ids,))
    cols = [d.name for d in cur.description]
    return {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}


def run(es, *, academic_year: str, study_year: int | None = None, semester: int | None = None,
        tech_term: str | None = None, course_code: str | None = None,
        neo4j=None, pg_conn=None) -> dict:
    """Полный федеративный запрос лаб. №2."""
    lectures = search_course_lectures(es, academic_year, study_year, semester,
                                      tech_term, course_code)

    courses: dict[int, dict] = {}
    for l in lectures:
        c = courses.setdefault(l["course_id"], {
            "course_id": l["course_id"], "course_code": l["course_code"],
            "course_title": l["course_title"], "study_year": l["study_year"],
            "semester": l["semester"], "academic_year": l["academic_year"],
            "lectures": [],
        })
        c["lectures"].append({"seq_no": l["seq_no"], "topic": l["topic"],
                              "planned_date": l.get("planned_date"),
                              "duration_acad_hours": 2,
                              "tech_requirements": l["tech_requirements"]})

    course_ids = sorted(courses)
    listeners: dict[int, int] = {}
    source_used = None
    if course_ids:
        if neo4j is not None:
            try:
                listeners = course_listeners_neo4j(neo4j, course_ids)
                source_used = "neo4j"
            except Exception:
                listeners = {}
        if not listeners and pg_conn is not None:
            listeners = course_listeners_pg(pg_conn, course_ids)
            source_used = "postgresql"

    details: dict[int, dict] = {}
    if course_ids and pg_conn is not None:
        try:
            details = course_details_pg(pg_conn, course_ids)
        except Exception:
            details = {}

    out_courses = []
    for cid in course_ids:
        c = courses[cid]
        c["lectures"].sort(key=lambda x: x["seq_no"])
        cap = listeners.get(cid, 0)
        det = details.get(cid, {})
        out_courses.append({
            **c,
            "description": det.get("description"),
            "is_elective": det.get("is_elective"),
            "lectures_count": len(c["lectures"]),
            "planned_acad_hours": len(c["lectures"]) * 2,   # 1 лекция = 2 ак. часа
            "listeners": cap,
            "required_auditorium_capacity": cap,
        })
    out_courses.sort(key=lambda x: x["required_auditorium_capacity"], reverse=True)

    return {
        "academic_year": academic_year, "study_year": study_year, "semester": semester,
        "tech_term": tech_term, "course_code": course_code,
        "listeners_source": source_used,
        "courses_count": len(out_courses),
        "courses": out_courses,
    }
