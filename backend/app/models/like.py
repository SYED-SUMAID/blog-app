from sqlmodel import SQLModel, Field


class Like(SQLModel, table=True):

    like_id: int | None = Field(default=None, primary_key=True)

    blog_id: int = Field(foreign_key="blog.blog_id")

    user_id: int = Field(foreign_key="user.id")