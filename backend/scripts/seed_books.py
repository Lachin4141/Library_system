"""
Loads cleaned_books.csv into the Books table via SQLAlchemy.
 
Usage (from the backend/scripts folder):
    python seed_books.py
"""
 
import sys
from pathlib import Path
import pandas as pd
 
# Absolute path to backend/app, regardless of where the script is run from.
APP_DIR = (Path(__file__).resolve().parent.parent / "app")
 
print(f"Looking for models.py and database.py in: {APP_DIR}")
print(f"models.py exists: {(APP_DIR / 'models.py').exists()}")
print(f"database.py exists: {(APP_DIR / 'database.py').exists()}")
 
# insert(0, ...) — put the path first so it's checked before anything else.
sys.path.insert(0, str(APP_DIR))
 
from database import Base, engine, SessionLocal  # noqa: E402
from models import Book  # noqa: E402
 
CLEANED_FILE = "../data/cleaned_books.csv"
 
 
def main():
    # Create tables if they don't exist yet
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
 
        # Commit in batches to avoid holding one giant transaction in memory
        if inserted % 1000 == 0:
            db.commit()
            print(f"  ...inserted {inserted}")
 
    db.commit()
    db.close()
    print(f"Done. Inserted: {inserted}, skipped (already existed): {skipped}")
 
 
if __name__ == "__main__":
    main()