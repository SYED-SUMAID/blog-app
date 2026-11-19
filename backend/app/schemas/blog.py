from datetime import datetime
from sqlmodel import SQLModel
from pydantic import BaseModel


# Data required to create a blog
class BlogCreate(BaseModel):
    title: str
    content: str


# Data returned by the API
class BlogResponse(SQLModel):
    blog_id: int
    title: str
    content: str
    author_id: int
    author_name: str
    created_at: datetime
