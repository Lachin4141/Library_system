"""
Pydantic-схемы: валидация входящих данных и формат ответов API.
"""

from pydantic import BaseModel, EmailStr, Field

from datetime import date

from models import RoleEnum, BorrowStatus, ReservationStatus


# ---------- Auth / Users ----------

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    # Самостоятельная регистрация создаёт ТОЛЬКО Student. Роль Administrator/Librarian
    # назначается отдельно — существующим администратором через PUT /users/{user_id}.


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: RoleEnum

    class Config:
        from_attributes = True  # позволяет строить схему прямо из SQLAlchemy-модели


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Books ----------

class BookCreate(BaseModel):
    isbn: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = None
    publisher: str | None = None
    year: int | None = None
    total_copies: int = Field(default=1, ge=1)


class BookUpdate(BaseModel):
    """Все поля опциональны — обновляем только то, что прислали (partial update)."""
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    year: int | None = None
    total_copies: int | None = Field(default=None, ge=1)


class BookOut(BaseModel):
    isbn: str
    title: str
    author: str | None
    publisher: str | None
    year: int | None
    total_copies: int
    available_copies: int

    class Config:
        from_attributes = True


class BookListOut(BaseModel):
    total: int
    items: list[BookOut]

# ---------- Borrow / Return ----------

class BorrowRequest(BaseModel):
    isbn: str = Field(..., min_length=1, max_length=20)


class ReturnRequest(BaseModel):
    isbn: str = Field(..., min_length=1, max_length=20)


class BorrowTransactionOut(BaseModel):
    transaction_id: int
    user_id: int
    isbn: str
    borrow_date: date
    due_date: date
    return_date: date | None
    status: BorrowStatus

    class Config:
        from_attributes = True


class BorrowHistoryOut(BaseModel):
    total: int
    items: list[BorrowTransactionOut]
    
# ---------- Reservations ----------

class ReservationRequest(BaseModel):
    isbn: str = Field(..., min_length=1, max_length=20)


class ReservationOut(BaseModel):
    reservation_id: int
    user_id: int
    isbn: str
    reservation_date: date
    status: ReservationStatus

    class Config:
        from_attributes = True


class ReservationListOut(BaseModel):
    total: int
    items: list[ReservationOut]
    
# ---------- Reports ----------

class MostBorrowedItem(BaseModel):
    isbn: str
    title: str
    borrow_count: int


class MostBorrowedListOut(BaseModel):
    items: list[MostBorrowedItem]


class ActiveUserItem(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    borrow_count: int


class ActiveUsersListOut(BaseModel):
    items: list[ActiveUserItem]


class CurrentlyBorrowedItem(BaseModel):
    transaction_id: int
    user_id: int
    user_full_name: str
    isbn: str
    book_title: str
    borrow_date: date
    due_date: date


class CurrentlyBorrowedListOut(BaseModel):
    total: int
    items: list[CurrentlyBorrowedItem]


class OverdueItem(BaseModel):
    transaction_id: int
    user_id: int
    user_full_name: str
    isbn: str
    book_title: str
    borrow_date: date
    due_date: date
    days_overdue: int


class OverdueListOut(BaseModel):
    total: int
    items: list[OverdueItem]


class MonthlyStatItem(BaseModel):
    year: int
    month: int
    borrow_count: int


class MonthlyStatsListOut(BaseModel):
    items: list[MonthlyStatItem]


# ---------- Admin: Users management ----------

class UserListItem(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: RoleEnum
    active_borrow_count: int
    total_borrow_count: int

    class Config:
        from_attributes = True


class UserListOut(BaseModel):
    total: int
    items: list[UserListItem]


class UserDetailOut(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: RoleEnum
    borrow_history: list[BorrowTransactionOut]
    reservations: list[ReservationOut]


class AdminUserUpdate(BaseModel):
    """Все поля опциональны — admin меняет только то, что прислал."""
    full_name: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6)
    role: RoleEnum | None = None


class AdminTransactionUpdate(BaseModel):
    """Ручная правка записи о выдаче — для исправления ошибок/статистики."""
    status: BorrowStatus | None = None
    due_date: date | None = None
    return_date: date | None = None