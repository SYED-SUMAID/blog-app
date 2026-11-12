from datetime import datetime
from sqlmodel import SQLModel, Field


class Comment(SQLModel, table=True):

    __tablename__ = "comment"

    comment_id: int | None = Field(default=None, primary_key=True)

    text: str

    blog_id: int = Field(
        foreign_key="blog.blog_id"
    )

    commenter_id: int = Field(
        foreign_key="user.id"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )