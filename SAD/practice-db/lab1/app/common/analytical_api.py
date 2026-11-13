"""Фабрика отдельных HTTP-приложений ЛР2 и ЛР3 с общей JWT-защитой."""
from datetime import date
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query

from app.common.analytics import rooms_report, hours_report
from app.common.security import current_user
from app.common.web import utf8_json


def create_app(number):
    app = FastAPI(title=f'Сервис ЛР №{number}', version='1.0.0')
    app.middleware('http')(utf8_json)

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': f'lab{number}'}

    if number == 2:
        @app.get('/report')
        def report(course_id: UUID, semester: int = Query(..., ge=1, le=12),
                   study_year: int = Query(..., ge=1, le=6),
                   academic_year: int = Query(..., ge=1900, le=2200),
                   trace: bool = False, user: dict = Depends(current_user)):
            if (semester + 1) // 2 != study_year:
                raise HTTPException(422, 'Семестр не соответствует году обучения')
            result = rooms_report(course_id, semester, study_year, academic_year)
            result['requested_by'] = user['sub']
            if not trace:
                result.pop('trace')
            return result
    else:
        @app.get('/report')
        def report(group_name: str = Query(..., min_length=1, max_length=50),
                   date_from: date = Query(...), date_to: date = Query(...),
                   tag: str = Query('спецдисциплина кафедры', min_length=1, max_length=100),
                   trace: bool = False, user: dict = Depends(current_user)):
            if date_from > date_to or not group_name.strip() or not tag.strip():
                raise HTTPException(422, 'Проверьте период, группу и тег')
            result = hours_report(group_name.strip(), date_from, date_to, tag.strip())
            result['requested_by'] = user['sub']
            if not trace:
                result.pop('trace')
            return result
    return app
