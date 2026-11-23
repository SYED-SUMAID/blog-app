from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class Blog(SQLModel, table=True):

    __tablename__ = "blog"

    blog_id: int | None = Field(default=None, primary_key=True)

    title: str

    content: str

    category: str | None = Field(default=None, index=True)

    author_id: int = Field(
        foreign_key="user.id",
        ondelete="CASCADE"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from sqlmodel import SQLModel


# Allowed categories (keep in sync with the frontend list)
CATEGORIES = [
    "Technology", "History", "Religion",
    "Fashion", "Markets", "Lifestyle", "General"
]

# The current frontend puts "[[category:Name]]" at the top of the content
CATEGORY_MARKER = re.compile(r"^\s*\[\[category:\s*([A-Za-z]+)\s*\]\]\s*")


def normalize_category(value: str | None) -> str | None:
    if value is None:
        return None

    for name in CATEGORIES:
        if name.lower() == value.strip().lower():
            return name

    raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")


# Data required to create a blog
class BlogCreate(BaseModel):
    title: str
    content: str
    category: str | None = None

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        return normalize_category(value)


# Data allowed when editing a blog (send only the fields to change)
class BlogUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    category: str | None = None

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        return normalize_category(value)


# Data returned by the API
class BlogResponse(SQLModel):
    blog_id: int
    title: str
    content: str
    category: str | None = None
    author_id: int
    author_name: str
    created_at: datetime    