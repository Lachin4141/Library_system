"""
Reporting and analytics endpoints (reports.py).
 
GET /reports/most-borrowed       — top books by number of loans
GET /reports/active-users        — most active users by number of loans
GET /reports/currently-borrowed  — books that are currently checked out
GET /reports/overdue             — overdue loans (and updates their status along the way)
GET /reports/monthly-stats       — loan statistics by month
 
The entire router is available only to Administrator and Librarian (dependencies at the router level).
Place this file at backend/app/routers/reports.py
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
    """Books sorted by number of loans (descending)."""
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
    """Users sorted by number of loans (descending)."""
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
    """All books that are currently checked out (status borrowed or overdue)."""
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
    Overdue loans: due_date is in the past, the book hasn't been returned yet.
 
    Before querying, "lazily" updates the status from borrowed to overdue for all
    transactions whose due_date has already passed — this keeps the status in the
    DB up to date on every call to this report, without a separate cron/scheduler.
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
    """Number of loans per month (year + month), in ascending date order."""
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