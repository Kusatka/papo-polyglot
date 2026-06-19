"""
Сервис лабораторной работы №1 (отдельный контейнер, HTTP API).

POST /report  — отчёт о 10 студентах с минимальным процентом посещения
                лекций, содержащих заданный термин/фразу, за период.
                Защищён JWT (Authorization: Bearer <token>).
GET  /health  — проверка живости (без авторизации).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from common.clients import get_es, get_redis, pg_session
from common.connections import wait_for_es, wait_for_postgres, wait_for_redis
from common.security import get_current_user
from . import query

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_postgres(); wait_for_redis(); wait_for_es()
    yield


app = FastAPI(title="ПАПО · Лаб.1 · Посещаемость по термину", lifespan=lifespan)


class Lab1Request(BaseModel):
    term: str = Field(..., examples=["партиционирование"],
                      description="Термин или фраза для поиска в содержании лекций")
    date_from: date = Field(..., examples=["2025-09-01"])
    date_to: date = Field(..., examples=["2026-06-30"])
    academic_year: str | None = Field(None, examples=["2025/2026"])
    limit: int = Field(10, ge=1, le=100)


@app.get("/health")
def health():
    return {"status": "ok", "service": "lab1"}


@app.post("/report")
def report(req: Lab1Request, user: str = Depends(get_current_user)):
    with pg_session() as conn:
        result = query.run(
            get_es(), conn, get_redis(),
            term=req.term,
            date_from=req.date_from.isoformat(),
            date_to=req.date_to.isoformat(),
            academic_year=req.academic_year,
            limit=req.limit,
        )
    result["requested_by"] = user
    return result
