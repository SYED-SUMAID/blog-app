from datetime import datetime
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)

    name: str

    username: str = Field(unique=True, index=True)

    hashed_password: str

    email: str = Field(unique=True)

    bio: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )