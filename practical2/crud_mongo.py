"""
Практическая №2 — CRUD в MongoDB (документ-композиция).
Данные: документ с данными и составом группы.
Цикл: создать коллекцию → добавить → прочитать по ключу → изменить → удалить → удалить коллекцию.
"""
from __future__ import annotations

COLL = "p2_groups"


def demo(db=None) -> list[str]:
    if db is None:
        from common.connections import mongo_client
        from common.config import get_settings
        db = mongo_client()[get_settings().mongo_db]
    log: list[str] = []

    # 1. Создать хранилище (коллекцию)
    db.drop_collection(COLL)
    col = db[COLL]
    log.append("1. Коллекция p2_groups создана")

    # 2. Добавить документ группы с составом
    doc = {
        "_id": "БСБО-01-23",
        "specialty": {"code": "38.03.05", "name": "Бизнес-информатика"},
        "students": [
            {"record_book_no": "23БСБО001", "fio": "Судовский Андрей Леонидович"},
            {"record_book_no": "23БСБО002", "fio": "Иванов Иван Иванович"},
        ],
    }
    col.insert_one(doc)
    log.append(f"2. Вставлен документ группы; студентов: {len(doc['students'])}")

    # 3. Прочитать по ключу (_id)
    found = col.find_one({"_id": "БСБО-01-23"})
    log.append(f"3. Чтение по ключу: специальность = {found['specialty']['name']}, "
               f"студентов = {len(found['students'])}")

    # 4. Изменить (добавить студента в состав)
    col.update_one({"_id": "БСБО-01-23"}, {"$push": {"students":
                   {"record_book_no": "23БСБО003", "fio": "Петрова Анна Сергеевна"}}})
    cnt = len(col.find_one({"_id": "БСБО-01-23"})["students"])
    log.append(f"4. Обновление ($push): студентов стало {cnt}")

    # 5. Удалить запись (документ)
    col.delete_one({"_id": "БСБО-01-23"})
    log.append(f"5. Документ удалён; осталось документов: {col.count_documents({})}")

    # 6. Удалить хранилище (коллекцию)
    db.drop_collection(COLL)
    log.append("6. Коллекция p2_groups удалена")
    return log


if __name__ == "__main__":
    print("\n".join(demo()))
