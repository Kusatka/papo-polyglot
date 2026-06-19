"""
Практическая №2 — CRUD в Redis (ключ-значение).
Данные: список студентов группы, ключ = номер зачётной книжки.
Цикл: создать → добавить → прочитать по ключу → изменить → удалить запись → удалить хранилище.
"""
from __future__ import annotations

NS = "p2:student:"          # пространство имён демонстрации
GROUP_KEY = "p2:group:БСБО-01-23"


def demo(r=None) -> list[str]:
    if r is None:
        from common.connections import redis_client
        r = redis_client()
    log: list[str] = []

    # 1. Создать хранилище (в Redis структура создаётся при первой записи)
    r.delete(GROUP_KEY)
    for k in r.scan_iter(f"{NS}*"):
        r.delete(k)
    log.append("1. Хранилище подготовлено (очищено пространство p2:*)")

    # 2. Добавить данные (ключ = зачётка)
    students = [
        ("23БСБО001", {"fio": "Судовский Андрей Леонидович", "group": "БСБО-01-23"}),
        ("23БСБО002", {"fio": "Иванов Иван Иванович", "group": "БСБО-01-23"}),
    ]
    for rbn, data in students:
        r.hset(f"{NS}{rbn}", mapping=data)
        r.sadd(GROUP_KEY, rbn)
    log.append(f"2. Добавлено студентов: {len(students)}; состав группы: {sorted(r.smembers(GROUP_KEY))}")

    # 3. Прочитать по ключу
    rec = r.hgetall(f"{NS}23БСБО001")
    log.append(f"3. Чтение по ключу 23БСБО001: {rec}")

    # 4. Изменить и сохранить
    r.hset(f"{NS}23БСБО001", "email", "sudovskiy@edu.example.ru")
    log.append(f"4. Обновление: email -> {r.hget(f'{NS}23БСБО001', 'email')}")

    # 5. Удалить запись
    r.delete(f"{NS}23БСБО002")
    r.srem(GROUP_KEY, "23БСБО002")
    log.append(f"5. Удалена запись 23БСБО002; состав группы: {sorted(r.smembers(GROUP_KEY))}")

    # 6. Удалить хранилище
    for k in r.scan_iter(f"{NS}*"):
        r.delete(k)
    r.delete(GROUP_KEY)
    log.append("6. Хранилище удалено (ключи p2:* удалены)")
    return log


if __name__ == "__main__":
    print("\n".join(demo()))
