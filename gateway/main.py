"""
API Gateway (единая точка входа, HTTP/JWT).

Отвечает за:
  • выдачу JWT по логину/паролю  — POST /auth/login;
  • аутентификацию всех защищённых вызовов (проверка Bearer-токена);
  • маршрутизацию вызовов к сервисам лабораторных работ (reverse proxy),
    пробрасывая Authorization-заголовок (сервис проверяет токен повторно).

Публичные методы API:
  POST /auth/login           — получить токен (form: username, password)
  POST /api/lab1/report      — отчёт лаб. №1 (мин. посещаемость по термину)
  POST /api/lab2/report      — отчёт лаб. №2 (вместимость аудитории)
  GET  /health               — статус шлюза
"""
from __future__ import annotations

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from common.config import get_settings
from common.security import authenticate_user, create_access_token, get_current_user

app = FastAPI(title="ПАПО · API Gateway", description="Единый шлюз с JWT-аутентификацией")
S = get_settings()


@app.get("/")
def root():
    return {
        "service": "ПАПО API Gateway",
        "auth": "POST /auth/login (username, password) -> JWT",
        "methods": ["POST /api/lab1/report", "POST /api/lab2/report"],
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    if not authenticate_user(form.username, form.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")
    token = create_access_token(form.username)
    return {"access_token": token, "token_type": "bearer"}


async def _proxy(target_base: str, path: str, request: Request, payload: dict):
    headers = {}
    auth = request.headers.get("authorization")
    if auth:
        headers["Authorization"] = auth
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(f"{target_base}{path}", json=payload, headers=headers)
        except httpx.RequestError as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Сервис недоступен: {e}")
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@app.post("/api/lab1/report")
async def lab1_report(payload: dict, request: Request, user: str = Depends(get_current_user)):
    """Прокси к сервису лаб. №1. Тело: {term, date_from, date_to, academic_year?, limit?}"""
    return await _proxy(S.lab1_url, "/report", request, payload)


@app.post("/api/lab2/report")
async def lab2_report(payload: dict, request: Request, user: str = Depends(get_current_user)):
    """Прокси к сервису лаб. №2. Тело: {academic_year, study_year?, semester?, tech_term?, course_code?}"""
    return await _proxy(S.lab2_url, "/report", request, payload)
