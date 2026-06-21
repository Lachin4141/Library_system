"""
Утилиты безопасности: хеширование паролей и создание/проверка JWT-токенов.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError

# ВАЖНО: в реальном проекте секретный ключ должен браться из переменной
# окружения и никогда не попадать в git. Значение ниже — только для разработки.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # токен живёт 24 часа


def hash_password(password: str) -> str:
    """Хеширует пароль перед сохранением в БД (используем bcrypt напрямую)."""
    # bcrypt физически не умеет работать с паролями длиннее 72 байт — обрезаем,
    # чтобы не получить ValueError на длинных паролях.
    password_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Сравнивает введённый пароль с хешем из БД."""
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создаёт JWT-токен с полезной нагрузкой data (например, {'sub': user_id})."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Проверяет и декодирует JWT-токен. Возвращает None, если токен невалиден/просрочен."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
