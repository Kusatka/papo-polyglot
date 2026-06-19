"""
Сервис лабораторной работы №2 (отдельный контейнер, HTTP API).

POST /report  — необходимый объём аудитории (число слушателей) для курса
                заданного семестра/года обучения + требования к тех. средствам.
                Защищён JWT.
GET  /health  — проверка живости.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from common.clients import get_es, get_neo4j, pg_session
from common.connections import wait_for_es, wait_for_neo4j, wait_for_postgres
from common.security import get_current_user
from . import query

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_postgres(); wait_for_es()
    try:
        wait_for_neo4j()
    except Exception:
        logging.warning("Neo4j недоступен на старте — будет использован PostgreSQL-резерв")
    yield


app = FastAPI(title="ПАПО · Лаб.2 · Вместимость аудитории", lifespan=lifespan)


class Lab2Request(BaseModel):
    academic_year: str = Field(..., examples=["2025/2026"])
    study_year: int | None = Field(None, ge=1, le=4, examples=[3],
                                   description="Год обучения (курс 1–4)")
    semester: int | None = Field(None, ge=1, le=2, examples=[1])
    tech_term: str | None = Field(None, examples=["компьютерный класс"],
                                  description="Требование к тех. средствам (полнотекст)")
    course_code: str | None = Field(None, examples=["БСБО-31-01"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "lab2"}


@app.post("/report")
def report(req: Lab2Request, user: str = Depends(get_current_user)):
    neo4j = None
    try:
        neo4j = get_neo4j()
    except Exception:
        neo4j = None
    with pg_session() as conn:
        result = query.run(
            get_es(), academic_year=req.academic_year, study_year=req.study_year,
            semester=req.semester, tech_term=req.tech_term, course_code=req.course_code,
            neo4j=neo4j, pg_conn=conn,
        )
    result["requested_by"] = user
    return result
