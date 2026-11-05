from datetime import datetime, timedelta, timezone
import os

import jwt
from pwdlib import PasswordHash

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database.connection import get_session
from app.models.user import User


# Password hashing
password_hash = PasswordHash.recommended()


# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# Hash a password
def hash_password(password: str):
    return password_hash.hash(password)


# Verify a password
def verify_password(plain_password: str, hashed_password: str):
    return password_hash.verify(plain_password, hashed_password)


# Create JWT access token
def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    token = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# Get the currently logged-in user
def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except jwt.InvalidTokenError:
        raise credentials_exception

    user = session.exec(
        select(User).where(User.id == int(user_id))
    ).first()

    if user is None:
        raise credentials_exception

    return user