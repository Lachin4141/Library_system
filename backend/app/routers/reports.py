"""
Эндпоинты отчётов и аналитики (reports.py).

GET /reports/most-borrowed       — топ книг по числу выдач
GET /reports/active-users        — самые активные пользователи по числу выдач
GET /reports/currently-borrowed  — книги, которые сейчас на руках
GET /reports/overdue             — просроченные выдачи (и попутно обновляет их статус)
GET /reports/monthly-stats       — статистика выдач по месяцам

Весь роутер доступен только Administrator и Librarian (dependencies на уровне router).
Кладите этот файл в backend/app/routers/reports.py
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from database import get_db
from models import Book, User, BorrowTransaction, BorrowStatus, RoleEnum
from schemas import (
    MostBorrowedListOut,
    MostBorrowedItem,
    ActiveUsersListOut,
    ActiveUserItem,
    CurrentlyBorrowedListOut,
    CurrentlyBorrowedItem,
    OverdueListOut,
    OverdueItem,
    MonthlyStatsListOut,
    MonthlyStatItem,
)
from auth.dependencies import require_role

router = APIRouter(
    dependencies=[Depends(require_role(RoleEnum.administrator, RoleEnum.librarian))]
)


@router.get("/reports/most-borrowed", response_model=MostBorrowedListOut)
def most_borrowed_books(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Книги, отсортированные по количеству выдач (по убыванию)."""
    rows = (
        db.query(
            Book.isbn,
            Book.title,
            func.count(BorrowTransaction.transaction_id).label("borrow_count"),
        )
        .join(BorrowTransaction, BorrowTransaction.isbn == Book.isbn)
        .group_by(Book.isbn, Book.title)
        .order_by(func.count(BorrowTransaction.transaction_id).desc())
        .limit(limit)
        .all()
    )
    items = [MostBorrowedItem(isbn=r.isbn, title=r.title, borrow_count=r.borrow_count) for r in rows]
    return MostBorrowedListOut(items=items)


@router.get("/reports/active-users", response_model=ActiveUsersListOut)
def active_users(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Пользователи, отсортированные по количеству выдач (по убыванию)."""
    rows = (
        db.query(
            User.user_id,
            User.full_name,
            User.email,
            func.count(BorrowTransaction.transaction_id).label("borrow_count"),
        )
        .join(BorrowTransaction, BorrowTransaction.user_id == User.user_id)
        .group_by(User.user_id, User.full_name, User.email)
        .order_by(func.count(BorrowTransaction.transaction_id).desc())
        .limit(limit)
        .all()
    )
    items = [
        ActiveUserItem(user_id=r.user_id, full_name=r.full_name, email=r.email, borrow_count=r.borrow_count)
        for r in rows
    ]
    return ActiveUsersListOut(items=items)


@router.get("/reports/currently-borrowed", response_model=CurrentlyBorrowedListOut)
def currently_borrowed(db: Session = Depends(get_db)):
    """Все книги, которые прямо сейчас на руках (status borrowed или overdue)."""
    rows = (
        db.query(BorrowTransaction, User.full_name, Book.title)
        .join(User, User.user_id == BorrowTransaction.user_id)
        .join(Book, Book.isbn == BorrowTransaction.isbn)
        .filter(BorrowTransaction.status.in_([BorrowStatus.borrowed, BorrowStatus.overdue]))
        .order_by(BorrowTransaction.due_date.asc())
        .all()
    )
    items = [
        CurrentlyBorrowedItem(
            transaction_id=t.transaction_id,
            user_id=t.user_id,
            user_full_name=full_name,
            isbn=t.isbn,
            book_title=title,
            borrow_date=t.borrow_date,
            due_date=t.due_date,
        )
        for t, full_name, title in rows
    ]
    return CurrentlyBorrowedListOut(total=len(items), items=items)


@router.get("/reports/overdue", response_model=OverdueListOut)
def overdue_books(db: Session = Depends(get_db)):
    """
    Просроченные выдачи: due_date в прошлом, книга ещё не возвращена.

    Перед выборкой "лениво" обновляет статус с borrowed на overdue для всех
    транзакций, у которых due_date уже прошёл — так статус в БД остаётся
    актуальным при каждом обращении к отчёту, без отдельного cron/scheduler.
    """
    today = date.today()

    stale = (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.status == BorrowStatus.borrowed,
            BorrowTransaction.due_date < today,
        )
        .all()
    )
    for t in stale:
        t.status = BorrowStatus.overdue
    if stale:
        db.commit()

    rows = (
        db.query(BorrowTransaction, User.full_name, Book.title)
        .join(User, User.user_id == BorrowTransaction.user_id)
        .join(Book, Book.isbn == BorrowTransaction.isbn)
        .filter(BorrowTransaction.status == BorrowStatus.overdue)
        .order_by(BorrowTransaction.due_date.asc())
        .all()
    )
    items = [
        OverdueItem(
            transaction_id=t.transaction_id,
            user_id=t.user_id,
            user_full_name=full_name,
            isbn=t.isbn,
            book_title=title,
            borrow_date=t.borrow_date,
            due_date=t.due_date,
            days_overdue=(today - t.due_date).days,
        )
        for t, full_name, title in rows
    ]
    return OverdueListOut(total=len(items), items=items)


@router.get("/reports/monthly-stats", response_model=MonthlyStatsListOut)
def monthly_stats(db: Session = Depends(get_db)):
    """Количество выдач по месяцам (год + месяц), по возрастанию даты."""
    rows = (
        db.query(
            extract("year", BorrowTransaction.borrow_date).label("year"),
            extract("month", BorrowTransaction.borrow_date).label("month"),
            func.count(BorrowTransaction.transaction_id).label("borrow_count"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )
    items = [MonthlyStatItem(year=int(r.year), month=int(r.month), borrow_count=r.borrow_count) for r in rows]
    return MonthlyStatsListOut(items=items)
