import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from sqlmodel import SQLModel


CATEGORIES = [
    "Technology",
    "History",
    "Religion",
    "Fashion",
    "Markets",
    "Lifestyle",
    "General"
]

CATEGORY_MARKER = re.compile(
    r"^\s*\[\[category:\s*([A-Za-z]+)\s*\]\]\s*"
)


def normalize_category(value: str | None) -> str | None:
    if value is None:
        return None

    for name in CATEGORIES:
        if name.lower() == value.strip().lower():
            return name

    raise ValueError(
        f"Category must be one of: {', '.join(CATEGORIES)}"
    )


class BlogCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    content: str | None = Field(default=None, min_length=1, max_length=20000)

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        return normalize_category(value)


class BlogUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    category: str | None = None

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        return normalize_category(value)


class BlogResponse(SQLModel):
    blog_id: int
    title: str
    content: str
    category: str | None = None
    author_id: int
    author_name: str
    created_at: datetime
