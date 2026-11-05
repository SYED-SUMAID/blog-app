from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)

    name: str

    username: str = Field(index=True, unique=True)

    hashed_password: str

    email: str = Field(unique=True)

    bio: str | None = None