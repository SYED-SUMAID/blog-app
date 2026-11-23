from sqlmodel import SQLModel, Field, UniqueConstraint


class Follow(SQLModel, table=True):

    __tablename__ = "userfollow"

    __table_args__ = (
        UniqueConstraint(
            "follower_id",
            "following_id",
            name="unique_user_follow"
        ),
    )

    follow_id: int | None = Field(default=None, primary_key=True)

    follower_id: int = Field(
        foreign_key="user.id",
        ondelete="CASCADE"
    )

    following_id: int = Field(
        foreign_key="user.id",
        ondelete="CASCADE"
    )
