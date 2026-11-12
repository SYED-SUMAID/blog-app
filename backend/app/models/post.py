from datetime import datetime

from sqlmodel import SQLModel, Field


class Post(SQLModel, table=True):

    __tablename__ = "post"

    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(
        foreign_key="user.id",
        ondelete="CASCADE",
        index=True
    )

    caption: str | None = Field(default=None)

    image_path: str = Field(max_length=500)

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )