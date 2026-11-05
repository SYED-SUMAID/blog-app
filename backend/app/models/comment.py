from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class Comment(SQLModel, table=True):

    comment_id: int | None = Field(default=None, primary_key=True)

    text: str

    blog_id: int = Field(foreign_key="blog.blog_id")

    commenter_id: int = Field(foreign_key="user.id")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )