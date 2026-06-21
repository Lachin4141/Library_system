"""
Pydantic-схемы: валидация входящих данных и формат ответов API.
"""

from pydantic import BaseModel, EmailStr, Field

from models import RoleEnum


# ---------- Auth / Users ----------

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    # По умолчанию — Student. На проде самостоятельный выбор роли Administrator/Librarian
    # стоило бы убрать и назначать роль отдельно через уже существующего администратора,
    # но для учебного проекта оставляем выбор открытым для удобства тестирования.
    role: RoleEnum = RoleEnum.student


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
