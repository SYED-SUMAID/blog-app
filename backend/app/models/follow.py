from sqlmodel import SQLModel, Field, UniqueConstraint


class Follow(SQLModel, table=True):

    __table_args__ = (
        UniqueConstraint(
            "follower_id",
            "following_id",
            name="unique_follow_relationship"
        ),
    )

    follow_id: int | None = Field(default=None, primary_key=True)

    follower_id: int = Field(foreign_key="user.id")

    following_id: int = Field(foreign_key="user.id")