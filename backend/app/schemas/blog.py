from pydantic import BaseModel


# Data required to create a blog
class BlogCreate(BaseModel):
    title: str
    content: str


# Data returned by the API
class BlogResponse(BaseModel):
    blog_id: int
    title: str
    content: str
    author_id: int
    author_name: str