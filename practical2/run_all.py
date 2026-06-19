"""
Практическая №2 — запуск CRUD-демонстраций по всем пяти хранилищам подряд.
Использование:  python -m practical2.run_all   (или через manage.py crud all)
"""
from __future__ import annotations

from . import crud_elasticsearch, crud_mongo, crud_neo4j, crud_postgres, crud_redis

DEMOS = [
    ("Redis (ключ-значение)", crud_redis.demo),
    ("MongoDB (документ-композиция)", crud_mongo.demo),
    ("Neo4j (типизированные связи)", crud_neo4j.demo),
    ("ElasticSearch (полнотекст)", crud_elasticsearch.demo),
    ("PostgreSQL (партиционирование)", crud_postgres.demo),
]


def main() -> None:
    for title, fn in DEMOS:
        print(f"\n===== {title} =====")
        try:
            for line in fn():
                print("   " + line)
        except Exception as e:  # noqa: BLE001
            print(f"   ОШИБКА: {e}")


if __name__ == "__main__":
    main()
