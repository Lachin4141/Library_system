"""
FastAPI dependencies (Depends) for checking the current user and their role.
 
We use HTTPBearer instead of OAuth2PasswordBearer because our /auth/login
accepts JSON (email + password) rather than the standard OAuth2 form. HTTPBearer
shows a simple "Authorize" button in Swagger where you can paste the token
returned by /auth/login.
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
    """Fetches the user from the DB by token. Raises 401 if the token is invalid."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
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
    Dependency factory for checking a user's role.
 
    Usage in a router:
        @router.post("/books", dependencies=[Depends(require_role(RoleEnum.administrator, RoleEnum.librarian))])
    """
 
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have sufficient permissions to perform this action",
            )
        return current_user
 
    return role_checker