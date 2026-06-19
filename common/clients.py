"""
Кэшированные клиенты хранилищ для сервисов (Gateway, lab1, lab2).

ES / Redis / Neo4j клиенты потокобезопасны — кэшируются (lru_cache).
PostgreSQL-соединение psycopg НЕ потокобезопасно — открывается на запрос
(контекстный менеджер pg_session()).
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

from . import connections as C


@lru_cache
def get_es():
    return C.es_client()


@lru_cache
def get_redis():
    return C.redis_client()


@lru_cache
def get_neo4j():
    return C.neo4j_driver()


@lru_cache
def get_mongo_db():
    from .config import get_settings
    return C.mongo_client()[get_settings().mongo_db]


@contextmanager
def pg_session():
    conn = C.pg_connect(autocommit=True)
    try:
        yield conn
    finally:
        conn.close()
