"""
JWT-аутентификация, общая для API Gateway и сервисов лабораторных работ.

Поток:
  1. Клиент шлёт логин/пароль на POST /auth/login (Gateway).
  2. Gateway проверяет учётные данные и выдаёт подписанный JWT (HS256).
  3. Клиент передаёт `Authorization: Bearer <token>` во все защищённые методы.
  4. И Gateway, и каждый сервис лабы независимо проверяют подпись и срок
     действия токена (defense-in-depth: сервис не доверяет факту, что запрос
     прошёл через шлюз).

Пароли хранятся в виде pbkdf2_sha256-хэшей (без нативных зависимостей).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from .config import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def _users() -> dict[str, str]:
    """Минимальная «таблица» пользователей. В реальной системе — отдельное
    хранилище; для учебного контура достаточно одного демо-пользователя."""
    s = get_settings()
    return {s.demo_user: pwd_context.hash(s.demo_password)}


def authenticate_user(username: str, password: str) -> bool:
    users = _users()
    if username not in users:
        return False
    return pwd_context.verify(password, users[username])


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_expire_minutes),
        "iss": "papo-api-gateway",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm],
                          options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Срок действия токена истёк")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Некорректный токен")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI-зависимость: возвращает имя пользователя из валидного токена,
    иначе 401. Подключается к любому защищённому методу через Depends()."""
    payload = decode_access_token(token)
    return str(payload["sub"])
