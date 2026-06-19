"""
Практическая №2 — CRUD в ElasticSearch (полнотекст + метаданные).
Данные: курс с полнотекстовым описанием.
Цикл: создать индекс → добавить → прочитать по id → полнотекстовый поиск →
      изменить → удалить документ → удалить индекс.
"""
from __future__ import annotations

INDEX = "p2_courses"
# Поля text используют встроенный русский анализатор (морфология/стемминг) —
# отдельный пользовательский анализатор не нужен.
MAPPING = {
    "mappings": {"properties": {
        "code": {"type": "keyword"},
        "title": {"type": "text", "analyzer": "russian"},
        "description": {"type": "text", "analyzer": "russian"},
        "semester": {"type": "short"},
    }},
}


def demo(es=None) -> list[str]:
    if es is None:
        from common.connections import es_client
        es = es_client()
    log: list[str] = []

    # 1. Создать хранилище (индекс с маппингом и русским анализатором)
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)
    es.indices.create(index=INDEX, **MAPPING)
    log.append("1. Индекс p2_courses создан (анализатор russian)")

    # 2. Добавить документ
    es.index(index=INDEX, id=1, document={
        "code": "PAPO", "title": "Проектирование архитектуры ПО",
        "description": "Микросервисы, API Gateway, партиционирование и потоковая обработка данных.",
        "semester": 1}, refresh=True)
    log.append("2. Документ id=1 проиндексирован")

    # 3. Прочитать по id
    doc = es.get(index=INDEX, id=1)["_source"]
    log.append(f"3. Чтение по id=1: {doc['title']}")

    # 4. Полнотекстовый поиск (по морфологии русского)
    hits = es.search(index=INDEX, query={"match": {"description": "партиционирование"}})
    log.append(f"4. Поиск 'партиционирование': найдено {hits['hits']['total']['value']} док.")

    # 5. Изменить документ
    es.update(index=INDEX, id=1, doc={"semester": 2}, refresh=True)
    log.append(f"5. Обновление: semester -> {es.get(index=INDEX, id=1)['_source']['semester']}")

    # 6a. Удалить документ
    es.delete(index=INDEX, id=1, refresh=True)
    log.append(f"6. Документ удалён; в индексе док.: {es.count(index=INDEX)['count']}")

    # 6b. Удалить хранилище (индекс)
    es.indices.delete(index=INDEX)
    log.append("7. Индекс p2_courses удалён")
    return log


if __name__ == "__main__":
    print("\n".join(demo()))
