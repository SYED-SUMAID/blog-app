from pydantic import BaseModel, Field


# Data required to create a comment
class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


# Data returned by the API
class CommentResponse(BaseModel):
    comment_id: int
    text: str
    blog_id: int
    commenter_id: int
    commenter_name: str