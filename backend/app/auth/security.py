"""
Security utilities: password hashing and JWT token creation/verification.
"""
 
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
 
import bcrypt
from jose import jwt, JWTError
 
# IMPORTANT: in a real project the secret key should come from an
# environment variable and never be committed to git. The value below is for development only.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # token lives for 24 hours
 
 
def hash_password(password: str) -> str:
    """Hashes a password before saving it to the DB (uses bcrypt directly)."""
    # bcrypt physically can't handle passwords longer than 72 bytes — truncate,
    # to avoid a ValueError on long passwords.
    password_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")
 
 
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares the entered password against the hash stored in the DB."""
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
 
 
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT token with payload data (e.g. {'sub': user_id})."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
 
 
def decode_access_token(token: str) -> Optional[dict]:
    """Verifies and decodes a JWT token. Returns None if the token is invalid/expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None