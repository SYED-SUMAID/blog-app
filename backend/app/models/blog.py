from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class Blog(SQLModel, table=True):

    blog_id: int | None = Field(default=None, primary_key=True)

    title: str

    content: str

    author_id: int = Field(foreign_key="user.id")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )