from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database.connection import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.security.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)


router = APIRouter()


# Register a new user
@router.post("/user", response_model=UserResponse, status_code=201)
def register_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):

    existing_user = session.exec(
        select(User).where(
            (User.username == user_data.username) |
            (User.email == user_data.email)
        )
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    new_user = User(
        name=user_data.name,
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        bio=user_data.bio
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user


# Login user
@router.post("/token")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):

    user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()

    if not user or not verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# Get currently logged-in user
@router.get("/user/me", response_model=UserResponse)
def get_user_profile(
    current_user: User = Depends(get_current_user)
):

    return current_user