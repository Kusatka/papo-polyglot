"""Прогон независимого оракула через ASGI TestClient и изолированный настоящий PostgreSQL.

PG_DSN должен указывать только на заранее подготовленную тестовую базу.
Docker networking и gateway этим прогоном не проверяются.
"""
import json
import os
import sys
from pathlib import Path

if not os.environ.get('PG_DSN'):
    raise RuntimeError('Задайте PG_DSN изолированной тестовой базы')
os.environ['JWT_SECRET'] = 'native-test-only-secret-at-least-32-bytes'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from fastapi.testclient import TestClient
from app.common.analytical_api import create_app
from app.common.security import issue_token
import verify_analytics as oracle

clients = {2: TestClient(create_app(2)), 3: TestClient(create_app(3))}


def snapshot(table):
    with psycopg.connect(os.environ['PG_DSN']) as conn:
        return conn.execute(f"SELECT coalesce(json_agg(t), '[]') FROM {table} t").fetchone()[0]


def api(path, params=None, token=None, data=None, expected=200):
    if path == '/auth/login':
        # Выпуск тестового токена; аутентификация gateway проверяется отдельно.
        return issue_token('teacher', 'teacher')
    number = int(path.split('/')[2][-1])
    response = clients[number].get('/report', params=params,
                                  headers={'Authorization': 'Bearer ' + token} if token else {})
    assert response.status_code == expected, (path, response.status_code, response.text)
    return response.json()


if __name__ == '__main__':
    oracle.snapshot = snapshot
    oracle.api = api
    oracle.main('verify_native.json')
    # Уточнить границы доказательства в сохранённом протоколе.
    path = Path(__file__).resolve().parents[1] / 'evidence' / 'verify_native.json'
    result = json.loads(path.read_text(encoding='utf-8'))
    result['execution'] = 'ASGI TestClient + native PostgreSQL; Docker/gateway excluded'
    with psycopg.connect(os.environ['PG_DSN']) as conn:
        result['postgres_version'] = conn.execute('SHOW server_version').fetchone()[0]
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Native verification saved:', path)
