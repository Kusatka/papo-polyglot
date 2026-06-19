#!/usr/bin/env python3
"""
Единая консоль управления стендом ПАПО.

Команды:
  python manage.py wait               ждать готовности всех 5 хранилищ
  python manage.py healthcheck        проверка доступности (практическая №1)
  python manage.py generate           заполнить все хранилища данными
  python manage.py regenerate         то же (для «мгновенного восстановления» на защите)
  python manage.py wipe               очистить все хранилища
  python manage.py crud <store|all>   CRUD-демо (практическая №2): redis|mongo|neo4j|es|postgres|all
  python manage.py token              выпустить демо-JWT (для ручных вызовов API)

Все параметры подключения берутся из .env / переменных окружения.
"""
from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def cmd_wait(_):
    from common.connections import wait_for_all
    wait_for_all()
    print("Все хранилища готовы.")


def cmd_healthcheck(_):
    from practical1.healthcheck import main
    return main()


def cmd_generate(_):
    from datagen.generate import generate_all
    stats = generate_all()
    print("Загрузка завершена. Объёмы по сущностям:")
    for k, v in stats.items():
        print(f"  {k:<14} {v}")


def cmd_wipe(_):
    from common import connections as C
    from common.config import get_settings
    from datagen.generate import LECTURES_INDEX
    s = get_settings()
    with C.pg_connect(s) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
    C.redis_client(s).flushdb()
    C.mongo_client(s)[s.mongo_db].drop_collection("groups")
    drv = C.neo4j_driver(s)
    with drv.session() as ses:
        ses.run("MATCH (n) DETACH DELETE n")
    drv.close()
    es = C.es_client(s)
    if es.indices.exists(index=LECTURES_INDEX):
        es.indices.delete(index=LECTURES_INDEX)
    print("Все хранилища очищены.")


def cmd_crud(args):
    from practical2 import (crud_elasticsearch, crud_mongo, crud_neo4j,
                            crud_postgres, crud_redis, run_all)
    mapping = {"redis": crud_redis.demo, "mongo": crud_mongo.demo, "neo4j": crud_neo4j.demo,
               "es": crud_elasticsearch.demo, "postgres": crud_postgres.demo}
    if args.store == "all":
        run_all.main()
    else:
        for line in mapping[args.store]():
            print(line)


def cmd_token(_):
    from common.security import create_access_token
    from common.config import get_settings
    print(create_access_token(get_settings().demo_user))


def main():
    p = argparse.ArgumentParser(description="Управление стендом ПАПО")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("wait")
    sub.add_parser("healthcheck")
    sub.add_parser("generate")
    sub.add_parser("regenerate")
    sub.add_parser("wipe")
    c = sub.add_parser("crud")
    c.add_argument("store", choices=["redis", "mongo", "neo4j", "es", "postgres", "all"])
    sub.add_parser("token")
    args = p.parse_args()

    handlers = {"wait": cmd_wait, "healthcheck": cmd_healthcheck, "generate": cmd_generate,
                "regenerate": cmd_generate, "wipe": cmd_wipe, "crud": cmd_crud, "token": cmd_token}
    return handlers[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
