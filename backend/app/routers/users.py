"""
Административные эндпоинты управления пользователями (users.py).

GET   /users               — список всех пользователей с краткой статистикой выдач
GET   /users/{user_id}     — детальная карточка: профиль + полная история выдач + резервации
PUT   /users/{user_id}     — изменить данные пользователя: имя, email, пароль, роль

Весь роутер доступен только Administrator.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import User, BorrowTransaction, Reservation, RoleEnum, BorrowStatus
from schemas import UserListOut, UserListItem, UserDetailOut, AdminUserUpdate
from auth.dependencies import require_role
from auth.security import hash_password

router = APIRouter(
    dependencies=[Depends(require_role(RoleEnum.administrator))]
)


def _borrow_counts(db: Session, user_id: int) -> tuple[int, int]:
    """Возвращает (активных_сейчас, всего) выдач для пользователя."""
    total = (
        db.query(func.count(BorrowTransaction.transaction_id))
        .filter(BorrowTransaction.user_id == user_id)
        .scalar()
    )
    active = (
        db.query(func.count(BorrowTransaction.transaction_id))
        .filter(
            BorrowTransaction.user_id == user_id,
            BorrowTransaction.status.in_([BorrowStatus.borrowed, BorrowStatus.overdue]),
        )
        .scalar()
    )
    return active, total


@router.get("", response_model=UserListOut)
def list_users(db: Session = Depends(get_db)):
    """Список всех пользователей с количеством выдач (активных сейчас и всего)."""
    users = db.query(User).order_by(User.user_id).all()

    items = []
    for u in users:
        active, total = _borrow_counts(db, u.user_id)
        items.append(
            UserListItem(
                user_id=u.user_id,
                full_name=u.full_name,
                email=u.email,
                role=u.role,
                active_borrow_count=active,
                total_borrow_count=total,
            )
        )

    return UserListOut(total=len(items), items=items)


@router.get("/{user_id}", response_model=UserDetailOut)
def get_user_detail(user_id: int, db: Session = Depends(get_db)):
    """Полная карточка пользователя: профиль + вся история выдач + все резервации (это и есть "логи")."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    history = (
        db.query(BorrowTransaction)
        .filter(BorrowTransaction.user_id == user_id)
        .order_by(BorrowTransaction.borrow_date.desc())
        .all()
    )
    reservations = (
        db.query(Reservation)
        .filter(Reservation.user_id == user_id)
        .order_by(Reservation.reservation_date.desc())
        .all()
    )

    return UserDetailOut(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        borrow_history=history,
        reservations=reservations,
    )


@router.put("/{user_id}", response_model=UserListItem)
def update_user(user_id: int, payload: AdminUserUpdate, db: Session = Depends(get_db)):
    """Изменить данные пользователя: имя, email, пароль, роль (всё опционально)."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != user.email:
        duplicate = (
            db.query(User)
            .filter(User.email == update_data["email"], User.user_id != user_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Этот email уже используется другим пользователем",
            )
        user.email = update_data["email"]

    if update_data.get("password"):
        user.password_hash = hash_password(update_data["password"])

    if "full_name" in update_data:
        user.full_name = update_data["full_name"]

    if "role" in update_data:
        user.role = update_data["role"]

    db.commit()
    db.refresh(user)

    active, total = _borrow_counts(db, user_id)
    return UserListItem(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        active_borrow_count=active,
        total_borrow_count=total,
    )
