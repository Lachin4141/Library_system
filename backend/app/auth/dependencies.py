"""
FastAPI-зависимости (Depends) для проверки текущего пользователя и его роли.

Используем HTTPBearer вместо OAuth2PasswordBearer, потому что наш /auth/login
принимает JSON (email + password), а не стандартную OAuth2-форму. HTTPBearer
показывает в Swagger простую кнопку "Authorize", куда можно вставить токен,
полученный из ответа /auth/login.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models import User, RoleEnum
from auth.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Достаёт пользователя из БД по токену. Бросает 401, если токен невалиден."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
    )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def require_role(*allowed_roles: RoleEnum):
    """
    Фабрика зависимостей для проверки роли пользователя.

    Использование в роутере:
        @router.post("/books", dependencies=[Depends(require_role(RoleEnum.administrator, RoleEnum.librarian))])
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас недостаточно прав для выполнения этого действия",
            )
        return current_user

    return role_checker
