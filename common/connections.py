"""
Фабрики клиентов для пяти хранилищ + ожидание готовности.

Каждая фабрика возвращает готовый клиент. Функции `wait_for_*` опрашивают
сервис с экспоненциальными ретраями (tenacity) — это нужно при старте через
docker compose, когда сервисы поднимаются не мгновенно, а также во время
защиты, когда хранилища перезапускаются.
"""
from __future__ import annotations

import logging

import psycopg
import redis as redis_lib
from elasticsearch import Elasticsearch
from neo4j import Driver, GraphDatabase
from pymongo import MongoClient
from tenacity import retry, stop_after_delay, wait_fixed

from .config import Settings, get_settings

log = logging.getLogger("papo.connections")

_WAIT = dict(wait=wait_fixed(2), stop=stop_after_delay(120), reraise=True)


# ── PostgreSQL ──────────────────────────────────────────────────────
def pg_connect(s: Settings | None = None, autocommit: bool = True) -> psycopg.Connection:
    s = s or get_settings()
    return psycopg.connect(s.postgres_dsn, autocommit=autocommit)


@retry(**_WAIT)
def wait_for_postgres(s: Settings | None = None) -> None:
    with pg_connect(s) as conn:
        conn.execute("SELECT 1")
    log.info("PostgreSQL готов")


# ── Redis ───────────────────────────────────────────────────────────
def redis_client(s: Settings | None = None) -> "redis_lib.Redis":
    s = s or get_settings()
    return redis_lib.Redis(host=s.redis_host, port=s.redis_port, db=s.redis_db,
                           decode_responses=True)


@retry(**_WAIT)
def wait_for_redis(s: Settings | None = None) -> None:
    redis_client(s).ping()
    log.info("Redis готов")


# ── MongoDB ─────────────────────────────────────────────────────────
def mongo_client(s: Settings | None = None) -> MongoClient:
    s = s or get_settings()
    return MongoClient(s.mongo_uri, serverSelectionTimeoutMS=5000)


@retry(**_WAIT)
def wait_for_mongo(s: Settings | None = None) -> None:
    mongo_client(s).admin.command("ping")
    log.info("MongoDB готов")


# ── Neo4j ───────────────────────────────────────────────────────────
def neo4j_driver(s: Settings | None = None) -> Driver:
    s = s or get_settings()
    return GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))


@retry(**_WAIT)
def wait_for_neo4j(s: Settings | None = None) -> None:
    drv = neo4j_driver(s)
    try:
        drv.verify_connectivity()
    finally:
        drv.close()
    log.info("Neo4j готов")


# ── ElasticSearch ───────────────────────────────────────────────────
def es_client(s: Settings | None = None) -> Elasticsearch:
    s = s or get_settings()
    return Elasticsearch(s.es_url, request_timeout=30)


@retry(**_WAIT)
def wait_for_es(s: Settings | None = None) -> None:
    if not es_client(s).ping():
        raise RuntimeError("ElasticSearch ещё не отвечает")
    log.info("ElasticSearch готов")


# ── Все сразу ───────────────────────────────────────────────────────
def wait_for_all(s: Settings | None = None) -> None:
    wait_for_postgres(s)
    wait_for_redis(s)
    wait_for_mongo(s)
    wait_for_neo4j(s)
    wait_for_es(s)
