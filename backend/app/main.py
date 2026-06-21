"""
Точка входа FastAPI-приложения Library Management System.

Запуск локально (из папки backend/app):
    uvicorn main:app --reload

После запуска документация Swagger доступна на /docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # noqa: F401  — импорт нужен, чтобы модели зарегистрировались в Base.metadata
from routers import auth as auth_router

app = FastAPI(
    title="Library Management System API",
    description="REST API для управления книгами, пользователями, выдачей и резервированием книг",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на проде сузить до конкретного домена фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Создаём таблицы при старте, если их ещё нет.
    # Когда подключим Alembic для миграций (Этап 3 плана), можно убрать.
    Base.metadata.create_all(bind=engine)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "library-management-system"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}


# Роутеры подключаем по мере готовности (Этапы 5-9 плана):
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])

# from routers import books, borrow, reservations, reports
# app.include_router(books.router, prefix="/books", tags=["books"])
# app.include_router(borrow.router, tags=["borrow"])
# app.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
# app.include_router(reports.router, prefix="/reports", tags=["reports"])
