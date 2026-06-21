"""
Authentication endpoints: registration, login, fetching the current user.
"""
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
 
from database import get_db
from models import User, RoleEnum
from schemas import UserRegister, UserLogin, UserOut, Token
from auth.security import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user
 
router = APIRouter()
 
 
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email is already registered",
        )
 
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=RoleEnum.student,  # self-service registration is always Student
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
 
 
@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Login: checks email/password, returns a JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
 
    access_token = create_access_token(
        data={"sub": str(user.user_id), "role": user.role.value}
    )
    return Token(access_token=access_token)
 
 
@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Returns the currently authenticated user's data (token check)."""
    return current_user