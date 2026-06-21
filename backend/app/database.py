"""
Database connection setup.
 
By default uses SQLite (convenient for development without Docker).
When PostgreSQL is running in docker-compose, simply override the
DATABASE_URL environment variable, e.g.:
    postgresql://user:password@db:5432/library
"""
 
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
 
# Absolute path: library.db always lives next to this file (backend/app/),
# regardless of which directory the command/script is launched from.
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "library.db"
 
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")
 
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
 
 
def get_db():
    """FastAPI dependency: opens a DB session and guarantees it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
 