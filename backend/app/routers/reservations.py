"""
Эндпоинты резервирования книг (reservations.py).

POST /reservations                  — создать резервацию (доступно, только если книги нет в наличии)
GET  /reservations/my               — личные резервации текущего пользователя (любой статус)
POST /reservations/{id}/cancel      — отменить свою резервацию (только пока статус pending)

Плюс служебная функция fulfill_oldest_pending_reservation(), которую вызывает
return_book() из routers/borrow.py при возврате книги: самая старая pending-резервация
на этот ISBN автоматически переводится в fulfilled.

Кладите этот файл в backend/app/routers/reservations.py
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
    """Создать резервацию книги. Доступно только если все экземпляры сейчас выданы."""
    book = db.query(Book).filter(Book.isbn == payload.isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

    if book.available_copies > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Книга сейчас доступна — оформите выдачу через /borrow, резервация не нужна",
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
            detail="У вас уже есть активная резервация на эту книгу",
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
    """Все резервации текущего пользователя — pending, fulfilled и cancelled."""
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
    """Отменить собственную резервацию. Отменить можно только резервацию со статусом pending."""
    reservation = (
        db.query(Reservation)
        .filter(
            Reservation.reservation_id == reservation_id,
            Reservation.user_id == current_user.user_id,
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Резервация не найдена")

    if reservation.status != ReservationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Нельзя отменить резервацию со статусом '{reservation.status.value}'",
        )

    reservation.status = ReservationStatus.cancelled
    db.commit()
    db.refresh(reservation)
    return reservation


def fulfill_oldest_pending_reservation(db: Session, isbn: str) -> Reservation | None:
    """
    Помечает самую старую pending-резервацию на данный ISBN как fulfilled.

    Вызывается из borrow.py -> return_book() при возврате книги: это сигнал
    "книга снова доступна, и по очереди она в первую очередь предназначена
    этому пользователю". Сама выдача всё равно оформляется обычным POST /borrow —
    эта функция только меняет статус резервации, не трогает available_copies
    (это уже делает return_book).

    Возвращает обновлённую резервацию, либо None, если очереди не было.
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
