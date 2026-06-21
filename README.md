# Library Management System

**WEX 328 — Work Experience 2025-2026 Spring Terms**

A full-stack web application for managing a library: book catalogue, user registration and roles, book borrowing and returns, reservations for unavailable books, transaction history, and analytics reports.

The initial book catalogue is loaded from the [Books Dataset (Book-Crossing) on Kaggle](https://www.kaggle.com/datasets/saurabhbagchi/books-dataset).

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend / API | FastAPI |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2 |
| Authentication | bcrypt (password hashing) + JWT (python-jose) |
| Frontend | HTML + CSS + Vanilla JS (single-page app) |
| Containerization | Docker + docker-compose |
| Version Control | Git / GitHub |

---

## Project Structure

```
library-management-system/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── database.py        # SQLAlchemy engine & session
│   │   ├── models.py          # ORM models
│   │   ├── schemas.py         # Pydantic schemas
│   │   └── routers/
│   │       ├── auth.py        # Register, login, /me
│   │       ├── books.py       # Book CRUD + search
│   │       ├── borrow.py      # Borrow & return
│   │       ├── reservations.py
│   │       ├── reports.py
│   │       └── users.py       # Admin user management
│   ├── scripts/
│   │   ├── clean_books.py     # Dataset cleaning
│   │   ├── seed_books.py      # Load books into DB
│   │   └── create_admin.py    # Create first admin account
│   ├── data/
│   │   └── cleaned_books.csv  # Cleaned dataset (not in git)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html             # Single-page frontend
│   ├── nginx.conf             # nginx reverse proxy config
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Database Schema

### Books
| Column | Type | Description |
|---|---|---|
| isbn | VARCHAR (PK) | Unique book identifier |
| title | VARCHAR | Book title |
| author | VARCHAR | Author name |
| publisher | VARCHAR | Publisher name |
| year | INTEGER | Publication year |
| total_copies | INTEGER | Total copies in library |
| available_copies | INTEGER | Copies available to borrow |

### Users
| Column | Type | Description |
|---|---|---|
| user_id | INTEGER (PK) | Auto-increment ID |
| full_name | VARCHAR | Full name |
| email | VARCHAR (unique) | Email address |
| password_hash | VARCHAR | bcrypt hash |
| role | ENUM | administrator / librarian / student |

### BorrowTransactions
| Column | Type | Description |
|---|---|---|
| transaction_id | INTEGER (PK) | Auto-increment ID |
| user_id | INTEGER (FK) | References users |
| isbn | VARCHAR (FK) | References books |
| borrow_date | DATE | Date borrowed |
| due_date | DATE | Return deadline (14 days) |
| return_date | DATE | Actual return date |
| status | ENUM | borrowed / returned / overdue |

### Reservations
| Column | Type | Description |
|---|---|---|
| reservation_id | INTEGER (PK) | Auto-increment ID |
| user_id | INTEGER (FK) | References users |
| isbn | VARCHAR (FK) | References books |
| reservation_date | DATE | Date reserved |
| status | ENUM | pending / fulfilled / cancelled |

---

## Quick Start with Docker

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/library-management-system.git
cd library-management-system
```

### 2. Create the environment file
```powershell
# Windows PowerShell
@"
POSTGRES_USER=library_user
POSTGRES_PASSWORD=library_pass
POSTGRES_DB=library_db
JWT_SECRET_KEY=my-secret-key-change-me
"@ | Out-File -FilePath .env -Encoding utf8
```
```bash
# Linux / macOS
cp .env.example .env
```

### 3. Build and start all containers
```bash
docker-compose up --build
```

Wait until you see:
```
library_backend | INFO:     Application startup complete.
```

### 4. Seed the database (first run only)
Open a second terminal in the same folder:

```bash
# Load book catalogue (~270k books from the Kaggle dataset)
docker-compose exec backend bash -c "cd /app/scripts && python seed_books.py"

# Create the first administrator account
docker-compose exec backend python scripts/create_admin.py
```

### 5. Open the application

| URL | Description |
|---|---|
| http://localhost | Frontend UI |
| http://localhost:8000/docs | Swagger API documentation |
| http://localhost:8000 | API root |
| localhost:5432 | PostgreSQL (for DBeaver / pgAdmin) |

---

## Running Locally (without Docker)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

cd app
uvicorn main:app --reload
```

Swagger docs: http://localhost:8000/docs

---

## API Endpoints

### Authentication
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/auth/register` | Register a new user (role: student) | Public |
| POST | `/auth/login` | Login, returns JWT token | Public |
| GET | `/auth/me` | Get current user info | Any logged-in user |

### Books
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/books` | List / search books (title, author, isbn, publisher) | Public |
| GET | `/books/{isbn}` | Get a single book | Public |
| POST | `/books` | Add a new book | Administrator, Librarian |
| PUT | `/books/{isbn}` | Update book info | Administrator, Librarian |
| DELETE | `/books/{isbn}` | Delete a book | Administrator, Librarian |

### Borrowing
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/borrow` | Borrow a book | Any logged-in user |
| POST | `/return` | Return a book | Any logged-in user |
| GET | `/borrow/history` | Personal borrow history | Any logged-in user |
| POST | `/borrow/{id}/force-return` | Force return (admin) | Administrator |
| PATCH | `/borrow/{id}` | Edit a transaction record | Administrator |

### Reservations
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/reservations` | Reserve an unavailable book | Any logged-in user |
| GET | `/reservations/my` | View personal reservations | Any logged-in user |
| POST | `/reservations/{id}/cancel` | Cancel a reservation | Any logged-in user |

### Reports
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/reports/most-borrowed` | Top borrowed books | Administrator, Librarian |
| GET | `/reports/active-users` | Most active users | Administrator, Librarian |
| GET | `/reports/currently-borrowed` | Books currently out | Administrator, Librarian |
| GET | `/reports/overdue` | Overdue books | Administrator, Librarian |
| GET | `/reports/monthly-stats` | Borrowing stats by month | Administrator, Librarian |

### Users (Admin)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/users` | List all users | Administrator |
| GET | `/users/{id}` | User detail + full history | Administrator |
| PUT | `/users/{id}` | Update user (name, email, role, password) | Administrator |

---

## User Roles

| Role | Permissions |
|---|---|
| **Student** | Browse books, borrow/return, reserve, view own history |
| **Librarian** | All student permissions + add/update/delete books + view reports |
| **Administrator** | All permissions + manage users + force returns + edit transactions |

> Self-registration always creates a **Student** account. To assign Librarian or Administrator roles, an existing admin uses `PUT /users/{id}`.

---

## Stopping the Application

```bash
# Stop containers (data is preserved)
docker-compose down

# Stop and delete all data (fresh start)
docker-compose down -v
```
