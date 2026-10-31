"""Сервис ЛР №1 (отдельный контейнер). Доступен только из сети Docker; вызов — через API Gateway."""
import logging
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query

from app.common.web import utf8_json
from app.common.security import current_user
from app.lab1.query import build_report

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)      # без строки на каждый внутренний HTTP-запрос
app = FastAPI(title='Сервис ЛР №1: посещаемость лекций по термину', version='1.0.0')
app.middleware('http')(utf8_json)


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'lab1'}


@app.get('/report')
def report(term: str = Query(..., min_length=2, max_length=200, description='термин или фраза'),
           date_from: date = Query(..., description='начало периода, ГГГГ-ММ-ДД'),
           date_to: date = Query(..., description='конец периода, ГГГГ-ММ-ДД'),
           limit: int = Query(10, ge=1, le=100), trace: bool = Query(False, description='вернуть шаги выполнения'),
           user: dict = Depends(current_user)):
    if date_from > date_to:
        raise HTTPException(422, 'date_from позже date_to')
    result = build_report(term.strip(), date_from, date_to, limit)
    result['requested_by'] = user['sub']
    if not trace:
        result.pop('trace')
    return result
