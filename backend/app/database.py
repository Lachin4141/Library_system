"""
Настройка подключения к базе данных.

По умолчанию используется SQLite (удобно для разработки без Docker).
Когда поднимем Postgres в docker-compose, просто переопределим переменную
окружения DATABASE_URL, например:
    postgresql://user:password@db:5432/library
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Абсолютный путь: library.db всегда лежит рядом с этим файлом (backend/app/),
# независимо от того, из какой папки запущена команда/скрипт.
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "library.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency для FastAPI: открывает сессию и гарантированно закрывает её."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
