"""
Генератор предметных данных для всех пяти хранилищ (единый источник истины).

build_dataset()  — детерминированно (по seed) строит согласованный набор:
                   кафедры, специальности, группы (вкл. БСБО-01-23 со студентом
                   Судовский А.Л.), курсы, лекции, записи и посещаемость.
load_*           — проекция набора в каждое хранилище (клиент можно передать
                   параметром — внедрение зависимостей).
generate_all()   — полный цикл: очистить → построить → загрузить во все 5.

Объёмы при GEN_GROUPS=34 (значение по умолчанию в .env): студентов ~1000+,
лекций ~1000+, записей ~6000+, посещаемость ~90000+ строк. Это обеспечивает
требование «~1000 строк на таблицу» и «мгновенное восстановление» данных на
защите (manage.py regenerate).
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from common.config import Settings, get_settings
from . import catalog as cat

log = logging.getLogger("papo.datagen")

ACADEMIC_YEAR = "2025/2026"
SEM1_START = date(2025, 9, 1)    # осенний семестр (понедельник)
SEM2_START = date(2026, 2, 9)    # весенний семестр (понедельник)
WEEKS_PER_SEM = 16
LECTURES_PER_COURSE = 16


@dataclass
class Dataset:
    departments: list[dict] = field(default_factory=list)
    specialties: list[dict] = field(default_factory=list)
    groups: list[dict] = field(default_factory=list)
    students: list[dict] = field(default_factory=list)
    tags: list[dict] = field(default_factory=list)
    courses: list[dict] = field(default_factory=list)
    course_tags: list[tuple[int, int]] = field(default_factory=list)
    lectures: list[dict] = field(default_factory=list)
    enrollments: list[dict] = field(default_factory=list)
    attendance: list[dict] = field(default_factory=list)

    def stats(self) -> dict[str, int]:
        return {
            "departments": len(self.departments), "specialties": len(self.specialties),
            "groups": len(self.groups), "students": len(self.students),
            "tags": len(self.tags), "courses": len(self.courses),
            "course_tags": len(self.course_tags), "lectures": len(self.lectures),
            "enrollments": len(self.enrollments), "attendance": len(self.attendance),
        }


# ════════════════════════════ ПОСТРОЕНИЕ ════════════════════════════
def build_dataset(s: Settings | None = None) -> Dataset:
    s = s or get_settings()
    rnd = random.Random(s.gen_seed)
    ds = Dataset()

    cid = {"dep": 0, "sp": 0, "grp": 0, "st": 0, "tag": 0, "crs": 0, "lec": 0, "enr": 0}

    def nxt(k):
        cid[k] += 1
        return cid[k]

    # ── кафедры ──
    dep_main = {"department_id": nxt("dep"), **cat.DEPARTMENT}
    dep_second = {"department_id": nxt("dep"), **cat.DEPARTMENT_SECOND}
    ds.departments += [dep_main, dep_second]

    # ── теги ──
    tag_special = {"tag_id": nxt("tag"), "name": cat.DEPT_SPECIAL_TAG}
    tag_elective = {"tag_id": nxt("tag"), "name": cat.ELECTIVE_TAG}
    ds.tags += [tag_special, tag_elective]

    # ── специальности ──
    for sp in cat.SPECIALTIES:
        ds.specialties.append({"specialty_id": nxt("sp"), "code": sp["code"],
                               "name": sp["name"], "department_id": dep_main["department_id"],
                               "prefix": sp["prefix"]})

    # ── группы ──
    enroll_years = [2022, 2023, 2024, 2025]   # -> курс 4,3,2,1 в 2025/26
    grp_counter: dict[tuple[str, int], int] = {}
    target = max(1, s.gen_groups)
    bsbo = next(sp for sp in ds.specialties if sp["prefix"] == "БСБО")
    plan: list[tuple[dict, int]] = [(bsbo, 2023)]   # БСБО-01-23 гарантированно первой
    made = 0
    while len(plan) < target:
        sp = ds.specialties[made % len(ds.specialties)]
        yr = enroll_years[(made // len(ds.specialties)) % len(enroll_years)]
        if not (sp is bsbo and yr == 2023):
            plan.append((sp, yr))
        made += 1
    plan = plan[:target]

    for sp, yr in plan:
        key = (sp["prefix"], yr)
        grp_counter[key] = grp_counter.get(key, 0) + 1
        num = grp_counter[key]
        code = f'{sp["prefix"]}-{num:02d}-{yr % 100:02d}'
        study_year = 2025 - yr + 1
        ds.groups.append({"group_id": nxt("grp"), "code": code,
                          "specialty_id": sp["specialty_id"], "year_enrolled": yr,
                          "study_year": max(1, min(4, study_year))})

    # ── студенты ──
    def make_fio(female):
        if female:
            return rnd.choice(cat.LAST_F), rnd.choice(cat.FIRST_F), rnd.choice(cat.MID_F)
        return rnd.choice(cat.LAST_M), rnd.choice(cat.FIRST_M), rnd.choice(cat.MID_M)

    for g in ds.groups:
        sp = next(x for x in ds.specialties if x["specialty_id"] == g["specialty_id"])
        n_students = rnd.randint(28, 34)
        for i in range(1, n_students + 1):
            sid = nxt("st")
            if g["code"] == cat.PINNED_STUDENT["group_code"] and i == 1:
                ln, fn, mn = (cat.PINNED_STUDENT["last_name"], cat.PINNED_STUDENT["first_name"],
                              cat.PINNED_STUDENT["middle_name"])
                rbn = cat.PINNED_STUDENT["record_book_no"]
            else:
                female = rnd.random() < 0.5
                ln, fn, mn = make_fio(female)
                rbn = f'{g["year_enrolled"] % 100:02d}{sp["prefix"]}{sid:03d}'
            byear = g["year_enrolled"] - rnd.randint(17, 19)
            ds.students.append({
                "student_id": sid, "record_book_no": rbn,
                "last_name": ln, "first_name": fn, "middle_name": mn,
                "group_id": g["group_id"],
                "email": f'{rbn.lower()}@edu.example.ru',
                "birth_date": date(byear, rnd.randint(1, 12), rnd.randint(1, 28)),
            })

    # ── курсы + лекции ──
    study_years_present = sorted({g["study_year"] for g in ds.groups})
    for sp in ds.specialties:
        for sy in study_years_present:
            disciplines = cat.YEAR_DISCIPLINES.get(sy, [])
            for sem in (1, 2):
                bucket = [d for idx, d in enumerate(disciplines) if idx % 2 == (sem - 1)]
                for idx, (title, terms, dept_special, elective) in enumerate(bucket, 1):
                    crs_id = nxt("crs")
                    dep_id = dep_main["department_id"] if dept_special else dep_second["department_id"]
                    code = f'{sp["prefix"]}-{sy}{sem}-{idx:02d}'
                    desc = (f'Дисциплина «{title}» специальности «{sp["name"]}». '
                            f'Изучаются темы: {", ".join(terms)}. '
                            f'Курс {sy}, семестр {sem}, {ACADEMIC_YEAR}.')
                    ds.courses.append({
                        "course_id": crs_id, "code": code, "title": title, "description": desc,
                        "department_id": dep_id, "study_year": sy, "semester": sem,
                        "academic_year": ACADEMIC_YEAR, "is_elective": elective,
                        "specialty_id": sp["specialty_id"], "terms": terms,
                        "dept_special": dept_special,
                    })
                    if dept_special:
                        ds.course_tags.append((crs_id, tag_special["tag_id"]))
                    if elective:
                        ds.course_tags.append((crs_id, tag_elective["tag_id"]))

                    tech_primary = cat.TECH_REQUIREMENTS[crs_id % len(cat.TECH_REQUIREMENTS)]
                    start = SEM1_START if sem == 1 else SEM2_START
                    weekday = crs_id % 5
                    for seq in range(1, LECTURES_PER_COURSE + 1):
                        term = terms[(seq - 1) % len(terms)]
                        topic = rnd.choice(cat.LECTURE_TOPIC_PATTERNS).format(term=term, course=title)
                        sentences = rnd.sample(cat.CONTENT_SENTENCES, k=3)
                        content = " ".join(x.format(term=term, course=title) for x in sentences)
                        content += f" Ключевые понятия: {', '.join(terms)}."
                        pdate = start + timedelta(weeks=seq - 1, days=weekday)
                        tech = tech_primary
                        if seq % 5 == 0:
                            tech = cat.TECH_REQUIREMENTS[(crs_id + seq) % len(cat.TECH_REQUIREMENTS)]
                        ds.lectures.append({
                            "lecture_id": nxt("lec"), "course_id": crs_id, "seq_no": seq,
                            "topic": topic, "content": content, "planned_date": pdate,
                            "duration_acad_hours": 2, "tech_requirements": tech,
                        })

    lectures_by_course: dict[int, list[dict]] = {}
    for lec in ds.lectures:
        lectures_by_course.setdefault(lec["course_id"], []).append(lec)
    courses_by_key: dict[tuple[int, int], list[dict]] = {}
    for c in ds.courses:
        courses_by_key.setdefault((c["specialty_id"], c["study_year"]), []).append(c)
    group_by_id = {g["group_id"]: g for g in ds.groups}

    # ── записи на курсы (вкл. курсы по выбору) + посещаемость ──
    for stu in ds.students:
        g = group_by_id[stu["group_id"]]
        key = (g["specialty_id"], g["study_year"])
        avail = courses_by_key.get(key, [])
        mandatory = [c for c in avail if not c["is_elective"]]
        electives = [c for c in avail if c["is_elective"]]
        chosen_el = (rnd.sample(electives, k=min(len(electives), rnd.randint(1, 2)))
                     if electives else [])
        base_rate = rnd.uniform(0.55, 0.97)
        for c in mandatory + chosen_el:
            ds.enrollments.append({
                "enrollment_id": nxt("enr"), "student_id": stu["student_id"],
                "course_id": c["course_id"], "is_elective": c["is_elective"],
            })
            for lec in lectures_by_course.get(c["course_id"], []):
                d = lec["planned_date"]
                iy, iw, _ = d.isocalendar()
                ds.attendance.append({
                    "student_id": stu["student_id"], "lecture_id": lec["lecture_id"],
                    "course_id": c["course_id"], "visit_date": d,
                    "iso_year": iy, "iso_week": iw,
                    "attended": rnd.random() < base_rate,
                })
    log.info("dataset built: %s", ds.stats())
    return ds


# ════════════════════════════ POSTGRESQL ════════════════════════════
def wipe_postgres(conn, schema_sql: str) -> None:
    cur = conn.cursor()
    cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
    cur.execute("CREATE SCHEMA public")
    cur.execute(schema_sql)


def load_postgres(ds: Dataset, conn, schema_sql: str, use_copy: bool = True) -> None:
    wipe_postgres(conn, schema_sql)
    cur = conn.cursor()
    cur.execute("SET client_min_messages TO warning")

    dmin = min(a["visit_date"] for a in ds.attendance)
    dmax = max(a["visit_date"] for a in ds.attendance)
    cur.execute("SELECT create_week_partitions(%s,%s)", (dmin, dmax))

    def copy_rows(table: str, cols: list[str], rows: list[tuple]):
        # COPY — основной быстрый путь загрузки; многострочный INSERT —
        # запасной вариант, если COPY недоступен.
        if not rows:
            return
        collist = ",".join(cols)
        if use_copy:
            with cur.copy(f"COPY {table} ({collist}) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row(r)
        else:
            placeholders = "(" + ",".join(["%s"] * len(cols)) + ")"
            chunk = 2000  # многострочный INSERT пачками — меньше сетевых обменов
            for i in range(0, len(rows), chunk):
                part = rows[i:i + chunk]
                values = ",".join([placeholders] * len(part))
                flat = [v for row in part for v in row]
                cur.execute(f"INSERT INTO {table} ({collist}) VALUES {values}", flat)

    copy_rows("department", ["department_id", "code", "name"],
              [(d["department_id"], d["code"], d["name"]) for d in ds.departments])
    copy_rows("specialty", ["specialty_id", "code", "name", "department_id"],
              [(x["specialty_id"], x["code"], x["name"], x["department_id"]) for x in ds.specialties])
    copy_rows("study_group", ["group_id", "code", "specialty_id", "year_enrolled"],
              [(g["group_id"], g["code"], g["specialty_id"], g["year_enrolled"]) for g in ds.groups])
    copy_rows("student", ["student_id", "record_book_no", "last_name", "first_name",
                          "middle_name", "group_id", "email", "birth_date"],
              [(s["student_id"], s["record_book_no"], s["last_name"], s["first_name"],
                s["middle_name"], s["group_id"], s["email"], s["birth_date"]) for s in ds.students])
    copy_rows("tag", ["tag_id", "name"], [(t["tag_id"], t["name"]) for t in ds.tags])
    copy_rows("course", ["course_id", "code", "title", "description", "department_id",
                         "study_year", "semester", "academic_year", "is_elective"],
              [(c["course_id"], c["code"], c["title"], c["description"], c["department_id"],
                c["study_year"], c["semester"], c["academic_year"], c["is_elective"]) for c in ds.courses])
    copy_rows("course_tag", ["course_id", "tag_id"], ds.course_tags)
    copy_rows("lecture", ["lecture_id", "course_id", "seq_no", "topic", "content",
                          "planned_date", "duration_acad_hours", "tech_requirements"],
              [(l["lecture_id"], l["course_id"], l["seq_no"], l["topic"], l["content"],
                l["planned_date"], l["duration_acad_hours"], l["tech_requirements"]) for l in ds.lectures])
    copy_rows("enrollment", ["enrollment_id", "student_id", "course_id", "is_elective"],
              [(e["enrollment_id"], e["student_id"], e["course_id"], e["is_elective"]) for e in ds.enrollments])
    copy_rows("attendance", ["student_id", "lecture_id", "course_id", "visit_date",
                             "iso_year", "iso_week", "attended"],
              [(a["student_id"], a["lecture_id"], a["course_id"], a["visit_date"],
                a["iso_year"], a["iso_week"], a["attended"]) for a in ds.attendance])

    for table, col in [("department", "department_id"), ("specialty", "specialty_id"),
                       ("study_group", "group_id"), ("student", "student_id"), ("tag", "tag_id"),
                       ("course", "course_id"), ("lecture", "lecture_id"), ("enrollment", "enrollment_id")]:
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}','{col}'), "
            f"COALESCE((SELECT MAX({col}) FROM {table}),1))")
    log.info("PostgreSQL loaded")


# ════════════════════════════ REDIS ═════════════════════════════════
def load_redis(ds: Dataset, client=None) -> None:
    from common.connections import redis_client
    r = client or redis_client()
    r.flushdb()
    group_code = {g["group_id"]: g["code"] for g in ds.groups}
    spec_name = {s["specialty_id"]: s["name"] for s in ds.specialties}
    grp_spec = {g["group_id"]: g["specialty_id"] for g in ds.groups}
    pipe = r.pipeline()
    for s in ds.students:
        gc = group_code[s["group_id"]]
        fio = " ".join(x for x in [s["last_name"], s["first_name"], s["middle_name"]] if x)
        pipe.hset(f'student:{s["record_book_no"]}', mapping={
            "student_id": s["student_id"], "record_book_no": s["record_book_no"],
            "fio": fio, "last_name": s["last_name"], "first_name": s["first_name"],
            "middle_name": s["middle_name"] or "", "group": gc,
            "specialty": spec_name[grp_spec[s["group_id"]]],
            "email": s["email"] or "", "birth_date": str(s["birth_date"]),
        })
        pipe.sadd(f'group:{gc}', s["record_book_no"])
    pipe.execute()
    log.info("Redis loaded")


# ════════════════════════════ MONGODB ═══════════════════════════════
def load_mongo(ds: Dataset, db=None) -> None:
    if db is None:
        from common.connections import mongo_client
        db = mongo_client()[get_settings().mongo_db]
    db.drop_collection("groups")
    spec = {s["specialty_id"]: s for s in ds.specialties}
    courses_by_id = {c["course_id"]: c for c in ds.courses}
    enr_by_student: dict[int, list[dict]] = {}
    for e in ds.enrollments:
        enr_by_student.setdefault(e["student_id"], []).append(e)
    students_by_group: dict[int, list[dict]] = {}
    for s in ds.students:
        students_by_group.setdefault(s["group_id"], []).append(s)

    docs = []
    for g in ds.groups:
        sp = spec[g["specialty_id"]]
        stud_docs = []
        for s in students_by_group.get(g["group_id"], []):
            crs = []
            for e in enr_by_student.get(s["student_id"], []):
                c = courses_by_id[e["course_id"]]
                crs.append({"course_id": c["course_id"], "code": c["code"], "title": c["title"],
                            "semester": c["semester"], "is_elective": e["is_elective"]})
            stud_docs.append({
                "student_id": s["student_id"], "record_book_no": s["record_book_no"],
                "fio": " ".join(x for x in [s["last_name"], s["first_name"], s["middle_name"]] if x),
                "email": s["email"], "birth_date": str(s["birth_date"]), "courses": crs,
            })
        docs.append({
            "_id": g["group_id"], "code": g["code"],
            "specialty": {"code": sp["code"], "name": sp["name"]},
            "year_enrolled": g["year_enrolled"], "study_year": g["study_year"],
            "students_count": len(stud_docs), "students": stud_docs,
        })
    if docs:
        db["groups"].insert_many(docs)
    log.info("MongoDB loaded")


# ════════════════════════════ NEO4J ═════════════════════════════════
def load_neo4j(ds: Dataset, driver=None) -> None:
    own = False
    if driver is None:
        from common.connections import neo4j_driver
        driver = neo4j_driver()
        own = True
    try:
        with driver.session() as ses:
            ses.run("MATCH (n) DETACH DELETE n")
            for label, prop in [("Specialty", "specialty_id"), ("Group", "group_id"),
                                ("Student", "student_id"), ("Course", "course_id"),
                                ("Lecture", "lecture_id")]:
                ses.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) "
                        f"REQUIRE n.{prop} IS UNIQUE")

            def batched(rows, size=1000):
                for i in range(0, len(rows), size):
                    yield rows[i:i + size]

            for b in batched(ds.specialties):
                ses.run("UNWIND $rows AS r CREATE (:Specialty {specialty_id:r.specialty_id,"
                        "code:r.code, name:r.name})", rows=b)
            for b in batched(ds.groups):
                ses.run("UNWIND $rows AS r CREATE (:Group {group_id:r.group_id, code:r.code,"
                        "study_year:r.study_year, year_enrolled:r.year_enrolled,"
                        "specialty_id:r.specialty_id})", rows=b)
            for b in batched([{"student_id": s["student_id"], "record_book_no": s["record_book_no"],
                               "fio": f'{s["last_name"]} {s["first_name"]} {s["middle_name"] or ""}'.strip(),
                               "group_id": s["group_id"]} for s in ds.students]):
                ses.run("UNWIND $rows AS r CREATE (:Student {student_id:r.student_id,"
                        "record_book_no:r.record_book_no, fio:r.fio, group_id:r.group_id})", rows=b)
            for b in batched(ds.courses):
                ses.run("UNWIND $rows AS r CREATE (:Course {course_id:r.course_id, code:r.code,"
                        "title:r.title, study_year:r.study_year, semester:r.semester,"
                        "academic_year:r.academic_year, is_elective:r.is_elective})", rows=b)
            for b in batched([{"lecture_id": l["lecture_id"], "course_id": l["course_id"],
                               "seq_no": l["seq_no"], "topic": l["topic"]} for l in ds.lectures]):
                ses.run("UNWIND $rows AS r CREATE (:Lecture {lecture_id:r.lecture_id,"
                        "course_id:r.course_id, seq_no:r.seq_no, topic:r.topic})", rows=b)
            for b in batched(ds.groups):
                ses.run("UNWIND $rows AS r MATCH (g:Group {group_id:r.group_id}),"
                        "(s:Specialty {specialty_id:r.specialty_id}) "
                        "CREATE (g)-[:OF_SPECIALTY]->(s)", rows=b)
            for b in batched([{"student_id": s["student_id"], "group_id": s["group_id"]} for s in ds.students]):
                ses.run("UNWIND $rows AS r MATCH (s:Student {student_id:r.student_id}),"
                        "(g:Group {group_id:r.group_id}) CREATE (s)-[:IN_GROUP]->(g)", rows=b)
            for b in batched([{"student_id": e["student_id"], "course_id": e["course_id"],
                               "is_elective": e["is_elective"]} for e in ds.enrollments]):
                ses.run("UNWIND $rows AS r MATCH (s:Student {student_id:r.student_id}),"
                        "(c:Course {course_id:r.course_id}) "
                        "CREATE (s)-[:ENROLLED {elective:r.is_elective}]->(c)", rows=b)
            for b in batched([{"course_id": l["course_id"], "lecture_id": l["lecture_id"]} for l in ds.lectures]):
                ses.run("UNWIND $rows AS r MATCH (c:Course {course_id:r.course_id}),"
                        "(l:Lecture {lecture_id:r.lecture_id}) CREATE (c)-[:HAS_LECTURE]->(l)", rows=b)
        log.info("Neo4j loaded")
    finally:
        if own:
            driver.close()


# ════════════════════════════ ELASTICSEARCH ═════════════════════════
LECTURES_INDEX = "lectures"
LECTURES_MAPPING = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {"properties": {
        "lecture_id": {"type": "integer"}, "course_id": {"type": "integer"},
        "seq_no": {"type": "short"},
        "topic": {"type": "text", "analyzer": "russian"},
        "content": {"type": "text", "analyzer": "russian"},
        "course_code": {"type": "keyword"},
        "course_title": {"type": "text", "analyzer": "russian", "fields": {"raw": {"type": "keyword"}}},
        "study_year": {"type": "short"}, "semester": {"type": "short"},
        "academic_year": {"type": "keyword"},
        "is_elective": {"type": "boolean"},
        "department_id": {"type": "integer"},
        "tech_requirements": {"type": "text", "analyzer": "russian"},
        "tags": {"type": "keyword"},
        "planned_date": {"type": "date"},
    }},
}


def es_actions(ds: Dataset):
    courses_by_id = {c["course_id"]: c for c in ds.courses}
    tagnames = {t["tag_id"]: t["name"] for t in ds.tags}
    tags_by_course: dict[int, list[str]] = {}
    for cid_, tid in ds.course_tags:
        tags_by_course.setdefault(cid_, []).append(tagnames[tid])
    for l in ds.lectures:
        c = courses_by_id[l["course_id"]]
        yield {
            "_index": LECTURES_INDEX, "_id": l["lecture_id"],
            "_source": {
                "lecture_id": l["lecture_id"], "course_id": c["course_id"], "seq_no": l["seq_no"],
                "topic": l["topic"], "content": l["content"],
                "course_code": c["code"], "course_title": c["title"],
                "study_year": c["study_year"], "semester": c["semester"],
                "academic_year": c["academic_year"], "is_elective": c["is_elective"],
                "department_id": c["department_id"],
                "tech_requirements": l["tech_requirements"],
                "tags": tags_by_course.get(c["course_id"], []),
                "planned_date": l["planned_date"].isoformat(),
            }}


def load_elasticsearch(ds: Dataset, client=None) -> None:
    from elasticsearch import helpers
    from common.connections import es_client
    es = client or es_client()
    if es.indices.exists(index=LECTURES_INDEX):
        es.indices.delete(index=LECTURES_INDEX)
    es.indices.create(index=LECTURES_INDEX, **LECTURES_MAPPING)
    helpers.bulk(es, es_actions(ds))
    es.indices.refresh(index=LECTURES_INDEX)
    log.info("ElasticSearch loaded")


# ════════════════════════════ ОРКЕСТРАЦИЯ ═══════════════════════════
def _schema_sql() -> str:
    import pathlib
    return pathlib.Path(__file__).resolve().parents[1].joinpath(
        "practical3", "schema.sql").read_text(encoding="utf-8")


def generate_all(s: Settings | None = None) -> dict[str, int]:
    s = s or get_settings()
    ds = build_dataset(s)
    from common.connections import pg_connect
    with pg_connect(s) as conn:
        load_postgres(ds, conn, _schema_sql())
    load_redis(ds)
    load_mongo(ds)
    load_neo4j(ds)
    load_elasticsearch(ds)
    return ds.stats()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(generate_all())
