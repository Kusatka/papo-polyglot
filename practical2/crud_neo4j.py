"""
Практическая №2 — CRUD в Neo4j (типизированные связи).
Данные: связи группа–студент–курс с учётом курсов по выбору.
Цикл: создать → добавить → прочитать → изменить → удалить связь/узел → очистить.
Демо-узлы помечаются меткой :P2 и свойством demo=true (чтобы не задеть данные лаб).
"""
from __future__ import annotations


def demo(driver=None) -> list[str]:
    own = False
    if driver is None:
        from common.connections import neo4j_driver
        driver = neo4j_driver(); own = True
    log: list[str] = []
    try:
        with driver.session() as s:
            # 1. Создать хранилище (очистить демо-граф)
            s.run("MATCH (n:P2) DETACH DELETE n")
            log.append("1. Демо-граф подготовлен (узлы :P2 очищены)")

            # 2. Добавить группу, студентов, курсы и связи (вкл. курс по выбору)
            s.run("""
                CREATE (g:P2:Group {code:'БСБО-01-23'})
                CREATE (s1:P2:Student {rbn:'23БСБО001', fio:'Судовский А.Л.'})
                CREATE (s2:P2:Student {rbn:'23БСБО002', fio:'Иванов И.И.'})
                CREATE (c1:P2:Course {code:'PAPO', title:'Проектирование архитектуры ПО'})
                CREATE (c2:P2:Course {code:'NOSQL', title:'NoSQL и полиглотное хранение'})
                CREATE (s1)-[:IN_GROUP]->(g)
                CREATE (s2)-[:IN_GROUP]->(g)
                CREATE (s1)-[:ENROLLED {elective:false}]->(c1)
                CREATE (s1)-[:ENROLLED {elective:true}]->(c2)
                CREATE (s2)-[:ENROLLED {elective:false}]->(c1)
            """)
            cnt = s.run("MATCH (n:P2) RETURN count(n) AS c").single()["c"]
            log.append(f"2. Создано узлов :P2 = {cnt} (группа, 2 студента, 2 курса) и связи")

            # 3. Прочитать: курсы студента 23БСБО001 (вкл. по выбору)
            rows = s.run("""MATCH (st:P2:Student {rbn:'23БСБО001'})-[e:ENROLLED]->(c:P2:Course)
                            RETURN c.title AS title, e.elective AS elective ORDER BY title""").data()
            log.append(f"3. Чтение (курсы Судовского): {rows}")

            # 4. Изменить: пометить запись на курс по выбору как обязательную
            s.run("""MATCH (:P2:Student {rbn:'23БСБО001'})-[e:ENROLLED]->(:P2:Course {code:'NOSQL'})
                     SET e.elective=false""")
            val = s.run("""MATCH (:P2:Student {rbn:'23БСБО001'})-[e:ENROLLED]->(:P2:Course {code:'NOSQL'})
                           RETURN e.elective AS el""").single()["el"]
            log.append(f"4. Обновление связи ENROLLED(NOSQL).elective -> {val}")

            # 5. Удалить связь (отчислить студента с курса)
            s.run("""MATCH (:P2:Student {rbn:'23БСБО002'})-[e:ENROLLED]->(:P2:Course {code:'PAPO'})
                     DELETE e""")
            left = s.run("MATCH (:P2:Student)-[e:ENROLLED]->() RETURN count(e) AS c").single()["c"]
            log.append(f"5. Удалена связь ENROLLED; осталось связей ENROLLED = {left}")

            # 6. Удалить хранилище (демо-граф)
            s.run("MATCH (n:P2) DETACH DELETE n")
            log.append("6. Демо-граф удалён (DETACH DELETE :P2)")
    finally:
        if own:
            driver.close()
    return log


if __name__ == "__main__":
    print("\n".join(demo()))
