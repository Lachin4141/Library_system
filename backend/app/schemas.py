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
