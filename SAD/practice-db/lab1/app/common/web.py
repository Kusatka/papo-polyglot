"""Общие настройки HTTP для шлюза и сервиса."""


async def utf8_json(request, call_next):
    """Явная кодировка в Content-Type ответов JSON: без неё часть клиентов (Invoke-RestMethod в
    Windows PowerShell 5.1) читает тело как ISO-8859-1 и портит кириллицу."""
    resp = await call_next(request)
    if resp.headers.get('content-type') == 'application/json':
        resp.headers['content-type'] = 'application/json; charset=utf-8'
    return resp
