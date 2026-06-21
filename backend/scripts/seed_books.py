"""
Загружает cleaned_books.csv в таблицу Books через SQLAlchemy.

Запуск (из папки backend/scripts):
    python seed_books.py
"""

import sys
from pathlib import Path
import pandas as pd

# Абсолютный путь к backend/app, независимо от того, откуда запущен скрипт.
APP_DIR = (Path(__file__).resolve().parent.parent / "app")

print(f"Ищу models.py и database.py в: {APP_DIR}")
print(f"models.py существует: {(APP_DIR / 'models.py').exists()}")
print(f"database.py существует: {(APP_DIR / 'database.py').exists()}")

# insert(0, ...) — ставим путь в начало, чтобы он проверялся первым.
sys.path.insert(0, str(APP_DIR))

from database import Base, engine, SessionLocal  # noqa: E402
from models import Book  # noqa: E402

CLEANED_FILE = "../data/cleaned_books.csv"


def main():
    # Создаём таблицы, если их ещё нет
    Base.metadata.create_all(bind=engine)

    df = pd.read_csv(CLEANED_FILE)
    db = SessionLocal()

    inserted, skipped = 0, 0
    for _, row in df.iterrows():
        if db.query(Book).filter(Book.isbn == row["isbn"]).first():
            skipped += 1
            continue

        book = Book(
            isbn=row["isbn"],
            title=row["title"],
            author=row["author"],
            publisher=row["publisher"],
            year=int(row["year"]) if pd.notna(row["year"]) else None,
            total_copies=1,
            available_copies=1,
        )
        db.add(book)
        inserted += 1

        # Коммитим пачками, чтобы не держать гигантскую транзакцию в памяти
        if inserted % 1000 == 0:
            db.commit()
            print(f"  ...добавлено {inserted}")

    db.commit()
    db.close()
    print(f"Готово. Добавлено: {inserted}, пропущено (уже существовали): {skipped}")


if __name__ == "__main__":
    main()
