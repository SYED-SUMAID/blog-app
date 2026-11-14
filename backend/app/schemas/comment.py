from pydantic import BaseModel


# Data required to create a comment
class CommentCreate(BaseModel):
    text: str


# Data returned by the API
class CommentResponse(BaseModel):
    comment_id: int
    text: str
    blog_id: int
    commenter_id: int
    commenter_name: str