<<<<<<< HEAD
\# Library Management System



Курсовой проект \*\*WEX 328 — Work Experience 2025-2026 Spring Terms\*\*.



Веб-приложение для управления книжным фондом библиотеки: каталог книг, регистрация

и роли пользователей, выдача/возврат книг, резервирование недоступных книг,

история транзакций и отчёты.



Начальный каталог книг загружается из датасета

\[Books Dataset (Book-Crossing) на Kaggle](https://www.kaggle.com/datasets/saurabhbagchi/books-dataset).



\## Технологический стек



| Слой | Технология |

|---|---|

| Backend / API | FastAPI |

| База данных | PostgreSQL (SQLite на этапе разработки) |

| ORM / миграции | SQLAlchemy + Alembic |

| Аутентификация | passlib (bcrypt) + JWT (python-jose) |

| Frontend | React / HTML+JS |

| Контейнеризация | Docker + docker-compose |



\## Структура проекта



```

library-management-system/

├── backend/

│   ├── app/

│   │   ├── main.py        # точка входа FastAPI

│   │   ├── database.py    # подключение к БД

│   │   ├── models.py      # модели Books, Users, BorrowTransactions, Reservations

│   │   └── routers/       # эндпоинты API (в разработке)

│   ├── scripts/

│   │   ├── clean\_books.py # очистка датасета Book-Crossing

│   │   └── seed\_books.py  # загрузка книг в БД

│   ├── data/               # сюда кладётся books.csv (не входит в git)

│   └── requirements.txt

├── frontend/                # в разработке

├── docker-compose.yml        # в разработке

└── README.md

```



\## Установка и запуск (локально, без Docker)



```bash

cd backend

python -m venv venv

source venv/bin/activate        # Windows: venv\\Scripts\\activate

pip install -r requirements.txt

```



\### 1. Загрузка начального каталога книг



Скачайте `books.csv` с Kaggle и положите в `backend/data/books.csv`, затем:



```bash

cd scripts

python clean\_books.py   # создаёт data/cleaned\_books.csv

python seed\_books.py    # загружает книги в БД (library.db)

```



\### 2. Запуск API



```bash

cd backend/app

uvicorn main:app --reload

```



Документация Swagger будет доступна на `http://localhost:8000/docs`.



\## База данных



Обязательные таблицы:



\- \*\*Books\*\* — ISBN, Book Title, Author, Publisher, Publication Year

\- \*\*Users\*\* — данные пользователя, роль (Administrator / Librarian / Student)

\- \*\*BorrowTransactions\*\* — transaction\_id, user\_id, isbn, borrow\_date, due\_date, return\_date, status

\- \*\*Reservations\*\* — reservation\_id, user\_id, isbn, reservation\_date, status



\## Статус разработки



\- \[x] Структура backend-проекта

\- \[x] Модели БД (Books, Users, BorrowTransactions, Reservations)

\- \[x] Очистка и импорт датасета книг

\- \[ ] Регистрация / логин / роли (auth)

\- \[ ] CRUD книг + поиск

\- \[ ] Выдача и возврат книг

\- \[ ] Резервирование книг

\- \[ ] Отчёты и аналитика

\- \[ ] Frontend

\- \[ ] Docker / docker-compose



\## API (план)



| Метод | Эндпоинт | Описание |

|---|---|---|

| GET | `/books` | Список / поиск книг |

| POST | `/books` | Добавить книгу |

| GET | `/users` | Список пользователей |

| POST | `/auth/register` | Регистрация |

| POST | `/auth/login` | Вход (JWT) |

| POST | `/borrow` | Выдача книги |

| POST | `/return` | Возврат книги |

| POST | `/reservations` | Резервирование книги |

| GET | `/reports` | Отчёты и аналитика |



=======
# Library_system
text
>>>>>>> 2bf0d1e9b62ae47acd18bd49fd3ef1bddf41523f
