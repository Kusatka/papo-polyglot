"""API Gateway: единая точка входа. Выдаёт JWT, проверяет его и маршрутизирует вызовы к сервисам лабораторных."""
import logging
import os
from datetime import date
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.common.web import utf8_json
from app.common.security import current_user, issue_token, load_users, verify_password

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)      # без строки на каждый внутренний HTTP-запрос
log = logging.getLogger('gateway')
LAB1_URL = os.environ.get('LAB1_URL', 'http://lab1:8001')
LAB2_URL = os.environ.get('LAB2_URL', 'http://lab2:8002')
LAB3_URL = os.environ.get('LAB3_URL', 'http://lab3:8003')
USERS = load_users()

app = FastAPI(title='API Gateway — Проектирование архитектуры ПО', version='1.0.0',
              description='Аутентификация по JWT (кнопка Authorize) и вызов аналитических запросов лабораторных работ.')
app.middleware('http')(utf8_json)


@app.get('/health', tags=['service'])
def health():
    try:
        lab1 = httpx.get(f'{LAB1_URL}/health', timeout=3).json()['status']
    except httpx.HTTPError:
        lab1 = 'unavailable'
    return {'status': 'ok', 'lab1': lab1}


@app.post('/auth/login', tags=['auth'], summary='Получить JWT по логину и паролю')
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = USERS.get(form.username)
    if not user or not verify_password(form.password, user['hash']):
        log.warning('неудачный вход: %s', form.username)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Неверный логин или пароль',
                            headers={'WWW-Authenticate': 'Bearer'})
    log.info('выдан токен: %s (%s)', form.username, user['role'])
    return issue_token(form.username, user['role'])


@app.get('/auth/me', tags=['auth'], summary='Сведения из токена')
def me(user: dict = Depends(current_user)):
    return user


@app.get('/api/lab1/report', tags=['lab1'],
         summary='ЛР №1: 10 студентов с минимальной посещаемостью лекций, содержащих термин, за период')
def lab1_report(request: Request,
                term: str = Query(..., min_length=2, max_length=200, examples=['партиционирование']),
                date_from: date = Query(..., examples=['2026-02-09']),
                date_to: date = Query(..., examples=['2026-04-05']),
                limit: int = Query(10, ge=1, le=100), trace: bool = Query(False),
                user: dict = Depends(current_user)):
    # токен уже проверен шлюзом; передаём его сервису, который проверяет подпись ещё раз
    params = {'term': term, 'date_from': date_from.isoformat(), 'date_to': date_to.isoformat(),
              'limit': limit, 'trace': str(trace).lower()}
    try:
        resp = httpx.get(f'{LAB1_URL}/report', params=params, timeout=30,
                         headers={'Authorization': request.headers['authorization']})
    except httpx.HTTPError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f'Сервис ЛР №1 недоступен: {e}')
    log.info('lab1 report: user=%s term=%r %s..%s -> %s', user['sub'], term, date_from, date_to, resp.status_code)
    try:
        return JSONResponse(resp.json(), status_code=resp.status_code)
    except ValueError:   # сервис ответил не JSON (внутренняя ошибка)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f'Сервис ЛР №1 вернул {resp.status_code}: {resp.text[:200]}')


def forward_report(url, request):
    """JWT проверен dependency шлюза; сервис выполняет повторную проверку."""
    try:
        response = httpx.get(f'{url}/report', params=request.query_params, timeout=30,
                             headers={'Authorization': request.headers['authorization']})
        return JSONResponse(response.json(), status_code=response.status_code)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'Сервис аналитического отчёта недоступен')


@app.get('/api/lab2/report', tags=['lab2'], summary='Вместимость аудитории и требования к технике')
def lab2_report(request: Request, course_id: UUID, semester: int = Query(..., ge=1, le=12),
                study_year: int = Query(..., ge=1, le=6),
                academic_year: int = Query(..., ge=1900, le=2200),
                trace: bool = False, user: dict = Depends(current_user)):
    return forward_report(LAB2_URL, request)


@app.get('/api/lab3/report', tags=['lab3'], summary='Плановые и посещённые академические часы группы')
def lab3_report(request: Request, group_name: str = Query(..., min_length=1, max_length=50),
                date_from: date = Query(...), date_to: date = Query(...),
                tag: str = Query('спецдисциплина кафедры', min_length=1, max_length=100),
                trace: bool = False, user: dict = Depends(current_user)):
    return forward_report(LAB3_URL, request)
