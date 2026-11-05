from sqlmodel import SQLModel, Field


class Follow(SQLModel, table=True):

    follow_id: int | None = Field(default=None, primary_key=True)

    follower_id: int = Field(foreign_key="user.id")

    following_id: int = Field(foreign_key="user.id")