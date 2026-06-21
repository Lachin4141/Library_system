"""
Book borrowing and return endpoints (borrow.py).
 
POST /borrow                          — borrow a book (current authenticated user)
POST /return                          — return a book
GET  /borrow/history                  — current user's personal transaction history
POST /borrow/{transaction_id}/force-return — forced return (Administrator)
PATCH /borrow/{transaction_id}        — manual edit of a borrow record (Administrator)
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
 
# Loan period — 14 days. Move to an environment variable if needed.
LOAN_PERIOD_DAYS = 14
 
 
@router.post("/borrow", response_model=BorrowTransactionOut, status_code=status.HTTP_201_CREATED)
def borrow_book(
    payload: BorrowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue a book to the current user, if copies are available."""
    book = db.query(Book).filter(Book.isbn == payload.isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
 
    if book.available_copies <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No copies of this book are available. Create a reservation.",
        )
 
    # Don't let a user borrow the same book a second time before returning the first
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
            detail="You've already borrowed this book and haven't returned it yet",
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
    """Shared return logic: used by both the self-service /return and admin force-return."""
    transaction.return_date = date.today()
    transaction.status = BorrowStatus.returned
 
    book = db.query(Book).filter(Book.isbn == transaction.isbn).first()
    if book:
        # min() in case total_copies was ever reduced manually
        book.available_copies = min(book.total_copies, book.available_copies + 1)
        # The book is available again — if there's a reservation queue, close the oldest pending one.
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
    """Return a book: closes the user's most recent active loan of this book."""
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
            detail="No active loan of this book was found for you",
        )
 
    return _do_return(db, transaction)
 
 
@router.get("/borrow/history", response_model=BorrowHistoryOut)
def my_borrow_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All transactions (current and past) for the current user."""
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
    """Forced return of a book by an administrator (e.g. the reader is unreachable / didn't return it on time)."""
    transaction = (
        db.query(BorrowTransaction)
        .filter(BorrowTransaction.transaction_id == transaction_id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
 
    if transaction.status == BorrowStatus.returned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This book has already been returned")
 
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
    """Manual edit of a borrow record (status/dates) — for fixing errors in the statistics."""
    transaction = (
        db.query(BorrowTransaction)
        .filter(BorrowTransaction.transaction_id == transaction_id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
 
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
 
    db.commit()
    db.refresh(transaction)
    return transaction