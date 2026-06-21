"""
Book reservation endpoints (reservations.py).
 
POST /reservations                  — create a reservation (only available when the book is out of stock)
GET  /reservations/my               — current user's personal reservations (any status)
POST /reservations/{id}/cancel      — cancel your own reservation (only while status is pending)
 
Plus the helper fulfill_oldest_pending_reservation(), which is called by
return_book() in routers/borrow.py when a book is returned: the oldest pending
reservation for that ISBN is automatically switched to fulfilled.
 
Place this file at backend/app/routers/reservations.py
"""
 
from datetime import date
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
 
from database import get_db
from models import Book, Reservation, ReservationStatus, User
from schemas import ReservationRequest, ReservationOut, ReservationListOut
from auth.dependencies import get_current_user
 
router = APIRouter()
 
 
@router.post("/reservations", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a book reservation. Only available when all copies are currently checked out."""
    book = db.query(Book).filter(Book.isbn == payload.isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
 
    if book.available_copies > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The book is currently available — borrow it via /borrow, a reservation isn't needed",
        )
 
    duplicate = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == current_user.user_id,
            Reservation.isbn == payload.isbn,
            Reservation.status == ReservationStatus.pending,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active reservation for this book",
        )
 
    reservation = Reservation(
        user_id=current_user.user_id,
        isbn=payload.isbn,
        reservation_date=date.today(),
        status=ReservationStatus.pending,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation
 
 
@router.get("/reservations/my", response_model=ReservationListOut)
def my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All of the current user's reservations — pending, fulfilled, and cancelled."""
    items = (
        db.query(Reservation)
        .filter(Reservation.user_id == current_user.user_id)
        .order_by(Reservation.reservation_date.desc())
        .all()
    )
    return ReservationListOut(total=len(items), items=items)
 
 
@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationOut)
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel your own reservation. Only a reservation with status pending can be cancelled."""
    reservation = (
        db.query(Reservation)
        .filter(
            Reservation.reservation_id == reservation_id,
            Reservation.user_id == current_user.user_id,
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
 
    if reservation.status != ReservationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a reservation with status '{reservation.status.value}'",
        )
 
    reservation.status = ReservationStatus.cancelled
    db.commit()
    db.refresh(reservation)
    return reservation
 
 
def fulfill_oldest_pending_reservation(db: Session, isbn: str) -> Reservation | None:
    """
    Marks the oldest pending reservation for the given ISBN as fulfilled.
 
    Called from borrow.py -> return_book() when a book is returned: this is a signal
    that "the book is available again, and by queue order it's earmarked first for
    this user." The actual loan is still created via a normal POST /borrow —
    this function only changes the reservation's status, it doesn't touch
    available_copies (return_book already does that).
 
    Returns the updated reservation, or None if there was no queue.
    """
    reservation = (
        db.query(Reservation)
        .filter(Reservation.isbn == isbn, Reservation.status == ReservationStatus.pending)
        .order_by(Reservation.reservation_date.asc(), Reservation.reservation_id.asc())
        .first()
    )
    if reservation:
        reservation.status = ReservationStatus.fulfilled
    return reservation