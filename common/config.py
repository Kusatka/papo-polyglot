"""
Единая конфигурация проекта.

Все параметры подключения к пяти хранилищам и настройки JWT берутся из
переменных окружения (см. .env). Значения по умолчанию соответствуют
сервисным именам внутри docker-сети, поэтому контейнеры «видят» друг друга
без дополнительной настройки. Для локального запуска вне docker достаточно
переопределить *_HOST на localhost.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── PostgreSQL ──
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "papo"
    postgres_user: str = "papo"
    postgres_password: str = "papo_pass"

    # ── Redis ──
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # ── MongoDB ──
    mongo_host: str = "mongo"
    mongo_port: int = 27017
    mongo_db: str = "papo"
    mongo_user: str = "papo"
    mongo_password: str = "papo_pass"

    # ── Neo4j ──
    neo4j_host: str = "neo4j"
    neo4j_bolt_port: int = 7687
    neo4j_http_port: int = 7474
    neo4j_user: str = "neo4j"
    neo4j_password: str = "papo_password"

    # ── ElasticSearch ──
    es_host: str = "elasticsearch"
    es_port: int = 9200
    es_scheme: str = "http"

    # ── JWT / Gateway ──
    jwt_secret: str = "change-me-super-secret-key-for-papo-2026"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    demo_user: str = "admin"
    demo_password: str = "admin"
    lab1_url: str = "http://lab1:8001"
    lab2_url: str = "http://lab2:8002"

    # ── Генерация данных ──
    gen_groups: int = 34
    gen_seed: int = 2023

    # Производные строки подключения ------------------------------------
    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mongo_uri(self) -> str:
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/?authSource=admin"
        )

    @property
    def neo4j_uri(self) -> str:
        return f"bolt://{self.neo4j_host}:{self.neo4j_bolt_port}"

    @property
    def es_url(self) -> str:
        return f"{self.es_scheme}://{self.es_host}:{self.es_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
