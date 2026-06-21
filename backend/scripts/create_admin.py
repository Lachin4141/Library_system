"""
Разовое создание первого администратора напрямую в базе данных.

Нужен, потому что обычная регистрация (POST /auth/register) теперь всегда
создаёт пользователя с ролью Student — иначе кто угодно мог бы
зарегистрироваться администратором. После того как первый админ создан,
дальше он сам назначает роли Librarian/Administrator другим пользователям
через PUT /users/{user_id} в самом приложении — этот скрипт больше не нужен.

Запуск (из backend/scripts):
    py create_admin.py
"""

import sys
from pathlib import Path

APP_DIR = (Path(__file__).resolve().parent.parent / "app")
sys.path.insert(0, str(APP_DIR))

from database import Base, engine, SessionLocal  # noqa: E402
from models import User, RoleEnum  # noqa: E402
from auth.security import hash_password  # noqa: E402


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("=== Создание первого администратора ===")
    full_name = input("Имя: ").strip()
    email = input("Email: ").strip()
    password = input("Пароль (мин. 6 символов): ").strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.role = RoleEnum.administrator
        existing.password_hash = hash_password(password)
        existing.full_name = full_name
        db.commit()
        print(f"Пользователь {email} уже существовал — обновлён до Administrator.")
    else:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=RoleEnum.administrator,
        )
        db.add(user)
        db.commit()
        print(f"Администратор {email} создан.")

    db.close()


if __name__ == "__main__":
    main()
