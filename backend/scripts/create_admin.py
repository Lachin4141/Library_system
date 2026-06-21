"""
One-off creation/promotion of an administrator directly in the database.
 
IMPORTANT about Docker: a backend started via docker-compose is connected to
Postgres INSIDE the container — that is NOT the same file as the local SQLite
database on Windows. Run this script in the same environment your backend
is actually running in:
 
  If backend runs in Docker:
      docker compose exec -it backend python /app/scripts/create_admin.py
 
  If backend runs locally (py -m uvicorn ...):
      cd backend/scripts
      py create_admin.py
 
The script prints the DATABASE_URL it connects to — compare it against the
one your running backend actually uses, so you don't accidentally create the
admin in the "wrong" database.
 
You can run it either:
  - interactively (no arguments — it will ask for name/email/password), or
  - non-interactively, by passing arguments directly:
        python create_admin.py --name "Lachin" --email admin@test.com --password "MyPass123"
"""
 
import argparse
import sys
from getpass import getpass
from pathlib import Path
 
APP_DIR = (Path(__file__).resolve().parent.parent / "app")
sys.path.insert(0, str(APP_DIR))
 
from database import Base, engine, SessionLocal, DATABASE_URL  # noqa: E402
from models import User, RoleEnum  # noqa: E402
from auth.security import hash_password  # noqa: E402
 
 
def parse_args():
    parser = argparse.ArgumentParser(description="Create or promote an administrator.")
    parser.add_argument("--name", help="User's full name")
    parser.add_argument("--email", help="User's email")
    parser.add_argument("--password", help="Password (min. 6 characters)")
    return parser.parse_args()
 
 
def prompt_text(value, label):
    if value:
        return value
    while True:
        entered = input(f"{label}: ").strip()
        if entered:
            return entered
        print("This field cannot be empty, please try again.")
 
 
def prompt_password(value):
    if value:
        if len(value) < 6:
            print("The password passed via --password is shorter than 6 characters — asking again.")
        else:
            return value
    while True:
        entered = getpass("Password (min. 6 characters, input is hidden): ").strip()
        if len(entered) >= 6:
            return entered
        print("Password must be at least 6 characters long.")
 
 
def main():
    args = parse_args()
 
    print("=== Create / promote administrator ===")
    print(f"Connecting to database: {DATABASE_URL}")
    print("(If this is not the same database your running backend uses — "
          "run this script in the same environment: locally or inside Docker.)\n")
 
    full_name = prompt_text(args.name, "Name")
    email = prompt_text(args.email, "Email")
    password = prompt_password(args.password)
 
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
 
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.role = RoleEnum.administrator
        existing.password_hash = hash_password(password)
        existing.full_name = full_name
        db.commit()
        db.refresh(existing)
        print(f"\nDone: user '{email}' (id={existing.user_id}) updated to Administrator.")
    else:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=RoleEnum.administrator,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"\nDone: administrator '{email}' (id={user.user_id}) created.")
 
    total_admins = db.query(User).filter(User.role == RoleEnum.administrator).count()
    print(f"Total administrators in this database: {total_admins}")
 
    db.close()
 
 
if __name__ == "__main__":
    main()