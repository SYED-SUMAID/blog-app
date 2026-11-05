from sqlmodel import SQLModel, Field, UniqueConstraint


class Like(SQLModel, table=True):

    __tablename__ = "liketracker"

    __table_args__ = (
        UniqueConstraint(
            "blog_id",
            "user_id",
            name="unique_blog_user_like"
        ),
    )

    like_id: int | None = Field(default=None, primary_key=True)

    blog_id: int = Field(foreign_key="blog.blog_id")

    user_id: int = Field(foreign_key="user.id")