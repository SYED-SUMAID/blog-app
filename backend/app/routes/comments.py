from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database.connection import get_session
from app.models.comment import Comment
from app.models.blog import Blog
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse
from app.security.auth import get_current_user


router = APIRouter()


# Add a comment
@router.post(
    "/blog/{blog_id}/comment",
    response_model=CommentResponse,
    status_code=201
)
def add_comment(
    blog_id: int,
    comment_data: CommentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):

    blog = session.get(Blog, blog_id)

    if not blog:
        raise HTTPException(
            status_code=404,
            detail="Blog not found"
        )

    new_comment = Comment(
        text=comment_data.text,
        blog_id=blog_id,
        commenter_id=current_user.id
    )

    session.add(new_comment)
    session.commit()
    session.refresh(new_comment)

    return new_comment


# Get all comments for a blog
@router.get(
    "/blog/{blog_id}/comments",
    response_model=list[CommentResponse]
)
def get_blog_comments(
    blog_id: int,
    session: Session = Depends(get_session)
):

    blog = session.get(Blog, blog_id)

    if not blog:
        raise HTTPException(
            status_code=404,
            detail="Blog not found"
        )

    comments = session.exec(
        select(Comment).where(Comment.blog_id == blog_id)
    ).all()

    return comments