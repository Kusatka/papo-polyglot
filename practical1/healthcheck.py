"""
Практическая №1 — проверка доступности всех пяти хранилищ и вывод сведений
о месте хранения данных и лог-записей (именованные тома docker).

Использование:  python -m practical1.healthcheck   (или manage.py healthcheck)
Код возврата 0 — все доступны, иначе 1.
"""
from __future__ import annotations

import sys

from common.config import get_settings

# Где каждое хранилище держит данные и логи (тома из docker-compose.yml)
STORAGE = {
    "PostgreSQL": ("том papo_pg_data → /var/lib/postgresql/data",
                   "том papo_pg_logs → /var/log/postgresql"),
    "Redis":      ("том papo_redis_data → /data (RDB+AOF)",
                   "том papo_redis_logs → /var/log/redis/redis.log"),
    "MongoDB":    ("том papo_mongo_data → /data/db",
                   "том papo_mongo_logs → /var/log/mongodb/mongod.log"),
    "Neo4j":      ("том papo_neo4j_data → /data",
                   "том papo_neo4j_logs → /logs"),
    "ElasticSearch": ("том papo_es_data → /usr/share/elasticsearch/data",
                      "том papo_es_logs → /usr/share/elasticsearch/logs"),
}


def _pg_ok(s):
    from common import connections as C
    conn = C.pg_connect(s)
    try:
        conn.execute("SELECT 1")
        return True
    finally:
        conn.close()


def _neo4j_ok(s):
    from common import connections as C
    drv = C.neo4j_driver(s)
    try:
        drv.verify_connectivity()
        return True
    finally:
        drv.close()


def _checks(s):
    from common import connections as C
    yield "PostgreSQL", lambda: _pg_ok(s)
    yield "Redis", lambda: C.redis_client(s).ping()
    yield "MongoDB", lambda: C.mongo_client(s).admin.command("ping")["ok"] == 1.0
    yield "Neo4j", lambda: _neo4j_ok(s)
    yield "ElasticSearch", lambda: C.es_client(s).ping()


def main() -> int:
    s = get_settings()
    print(f"{'Хранилище':<15}{'Статус':<12}{'Данные / логи'}")
    print("-" * 92)
    all_ok = True
    for name, check in _checks(s):
        try:
            ok = bool(check())
        except Exception as e:  # noqa: BLE001
            ok = False
            err = str(e).splitlines()[0][:40]
        data_loc, log_loc = STORAGE[name]
        status = "ДОСТУПНО" if ok else "НЕДОСТУПНО"
        print(f"{name:<15}{status:<12}{data_loc}")
        print(f"{'':<27}{log_loc}")
        if not ok:
            all_ok = False
            print(f"{'':<27}причина: {err}")
    print("-" * 92)
    print("ИТОГ:", "все хранилища доступны" if all_ok else "есть недоступные хранилища")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
