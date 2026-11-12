from datetime import datetime
from sqlmodel import SQLModel, Field


class Blog(SQLModel, table=True):

    __tablename__ = "blog"

    blog_id: int | None = Field(default=None, primary_key=True)

    title: str

    content: str

    author_id: int = Field(
        foreign_key="user.id"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )