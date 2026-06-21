"""
Эндпоинты выдачи и возврата книг (borrow.py).

POST /borrow                          — взять книгу (текущий авторизованный пользователь)
POST /return                          — вернуть книгу
GET  /borrow/history                  — личная история транзакций текущего пользователя
POST /borrow/{transaction_id}/force-return — принудительный возврат (Administrator)
PATCH /borrow/{transaction_id}        — ручная правка записи о выдаче (Administrator)
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Book, BorrowTransaction, BorrowStatus, User, RoleEnum
from schemas import (
    BorrowRequest,
    ReturnRequest,
    BorrowTransactionOut,
    BorrowHistoryOut,
    AdminTransactionUpdate,
)
from auth.dependencies import get_current_user, require_role
from routers.reservations import fulfill_oldest_pending_reservation

router = APIRouter()

# Срок выдачи книги — 14 дней. При желании вынести в переменную окружения.
LOAN_PERIOD_DAYS = 14


@router.post("/borrow", response_model=BorrowTransactionOut, status_code=status.HTTP_201_CREATED)
def borrow_book(
    payload: BorrowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Выдать книгу текущему пользователю, если есть доступные экземпляры."""
    book = db.query(Book).filter(Book.isbn == payload.isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

    if book.available_copies <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет доступных экземпляров этой книги. Создайте резервацию.",
        )

    # Не даём пользователю взять одну и ту же книгу второй раз, пока не вернул первую
    already_borrowed = (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.user_id == current_user.user_id,
            BorrowTransaction.isbn == payload.isbn,
            BorrowTransaction.status == BorrowStatus.borrowed,
        )
        .first()
    )
    if already_borrowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже взяли эту книгу и ещё не вернули её",
        )

    today = date.today()
    transaction = BorrowTransaction(
        user_id=current_user.user_id,
        isbn=payload.isbn,
        borrow_date=today,
        due_date=today + timedelta(days=LOAN_PERIOD_DAYS),
        status=BorrowStatus.borrowed,
    )
    book.available_copies -= 1

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def _do_return(db: Session, transaction: BorrowTransaction) -> BorrowTransaction:
    """Общая логика возврата: используется и self-service /return, и admin force-return."""
    transaction.return_date = date.today()
    transaction.status = BorrowStatus.returned

    book = db.query(Book).filter(Book.isbn == transaction.isbn).first()
    if book:
        # min() на случай, если total_copies когда-то уменьшали вручную
        book.available_copies = min(book.total_copies, book.available_copies + 1)
        # Книга снова доступна — если есть очередь резерваций, закрываем самую старую pending.
        fulfill_oldest_pending_reservation(db, transaction.isbn)

    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/return", response_model=BorrowTransactionOut)
def return_book(
    payload: ReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Вернуть книгу: закрывает самую свежую активную выдачу этой книги у пользователя."""
    transaction = (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.user_id == current_user.user_id,
            BorrowTransaction.isbn == payload.isbn,
            BorrowTransaction.status.in_([BorrowStatus.borrowed, BorrowStatus.overdue]),
        )
        .order_by(BorrowTransaction.borrow_date.desc())
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активная выдача этой книги у вас не найдена",
        )

    return _do_return(db, transaction)


@router.get("/borrow/history", response_model=BorrowHistoryOut)
def my_borrow_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """История всех транзакций (текущих и прошлых) текущего пользователя."""
    items = (
        db.query(BorrowTransaction)
        .filter(BorrowTransaction.user_id == current_user.user_id)
        .order_by(BorrowTransaction.borrow_date.desc())
        .all()
    )
    return BorrowHistoryOut(total=len(items), items=items)


@router.post(
    "/borrow/{transaction_id}/force-return",
    response_model=BorrowTransactionOut,
    dependencies=[Depends(require_role(RoleEnum.administrator))],
)
def force_return_book(transaction_id: int, db: Session = Depends(get_db)):
    """Принудительный возврат книги администратором (например, читатель недоступен / не вернул вовремя)."""
    transaction = (
        db.query(BorrowTransaction)
        .filter(BorrowTransaction.transaction_id == transaction_id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Транзакция не найдена")

    if transaction.status == BorrowStatus.returned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Эта книга уже возвращена")

    return _do_return(db, transaction)


@router.patch(
    "/borrow/{transaction_id}",
    response_model=BorrowTransactionOut,
    dependencies=[Depends(require_role(RoleEnum.administrator))],
)
def admin_edit_transaction(
    transaction_id: int,
    payload: AdminTransactionUpdate,
    db: Session = Depends(get_db),
):
    """Ручная правка записи о выдаче (статус/сроки) — для исправления ошибок в статистике."""
    transaction = (
        db.query(BorrowTransaction)
        .filter(BorrowTransaction.transaction_id == transaction_id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Транзакция не найдена")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return transaction
