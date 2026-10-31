"""JWT-аутентификация, общая для шлюза и сервиса ЛР №1.

Шлюз выдаёт токен (POST /auth/login) и проверяет его на каждом вызове API; сервис ЛР №1 проверяет
тот же токен повторно (общий секрет HS256), поэтому вызвать его в обход шлюза без токена нельзя.
Пароли пользователей хранятся только в виде PBKDF2-SHA256 с солью (переменная GATEWAY_USERS).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET = os.environ.get('JWT_SECRET', '')
ALGORITHM = 'HS256'
ISSUER = 'papo-gateway'
TTL_MIN = int(os.environ.get('JWT_TTL_MIN', '60'))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


def hash_password(password: str, iterations: int = 200_000) -> str:
    """Строка вида pbkdf2_sha256:<итерации>:<соль>:<хеш> (без символа $, чтобы не мешать .env/compose)."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
    return f'pbkdf2_sha256:{iterations}:{base64.b64encode(salt).decode()}:{base64.b64encode(dk).decode()}'


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = stored.split(':')
        if algo != 'pbkdf2_sha256':
            return False
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt), int(iters))
        return hmac.compare_digest(dk, base64.b64decode(digest))   # сравнение за постоянное время
    except ValueError:
        return False


def load_users() -> dict[str, dict]:
    """GATEWAY_USERS = 'логин|роль|хеш;логин|роль|хеш'"""
    users = {}
    for item in filter(None, os.environ.get('GATEWAY_USERS', '').split(';')):
        login, role, pw_hash = item.split('|')
        users[login.strip()] = {'role': role.strip(), 'hash': pw_hash.strip()}
    return users


def issue_token(username: str, role: str) -> dict:
    now = int(time.time())
    claims = {'sub': username, 'role': role, 'iss': ISSUER, 'iat': now, 'exp': now + TTL_MIN * 60}
    return {'access_token': jwt.encode(claims, SECRET, algorithm=ALGORITHM), 'token_type': 'bearer',
            'expires_in': TTL_MIN * 60}


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM], issuer=ISSUER, options={'require': ['exp', 'sub']})


def current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return decode_token(token)
    except jwt.ExpiredSignatureError:
        detail = 'Срок действия токена истёк'
    except jwt.PyJWTError as e:
        detail = f'Недействительный токен: {e}'
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers={'WWW-Authenticate': 'Bearer'})
