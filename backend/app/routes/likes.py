from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database.connection import get_session
from app.models.like import Like
from app.models.blog import Blog
from app.models.user import User
from app.security.auth import get_current_user


router = APIRouter()


# Like a blog
@router.post("/blog/{blog_id}/like")
def like_blog(
    blog_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):

    # Check if the blog exists
    blog = session.get(Blog, blog_id)

    if not blog:
        raise HTTPException(
            status_code=404,
            detail="Blog not found"
        )

    # Check if the user has already liked this blog
    existing_like = session.exec(
        select(Like).where(
            (Like.blog_id == blog_id) &
            (Like.user_id == current_user.id)
        )
    ).first()

    if existing_like:
        raise HTTPException(
            status_code=400,
            detail="You have already liked this blog"
        )

    # Create a new like
    new_like = Like(
        blog_id=blog_id,
        user_id=current_user.id
    )

    session.add(new_like)
    session.commit()

    return {"message": "Blog liked successfully"}


# Unlike a blog
@router.delete("/blog/{blog_id}/like")
def unlike_blog(
    blog_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):

    # Find the like
    existing_like = session.exec(
        select(Like).where(
            (Like.blog_id == blog_id) &
            (Like.user_id == current_user.id)
        )
    ).first()

    if not existing_like:
        raise HTTPException(
            status_code=404,
            detail="Like not found"
        )

    session.delete(existing_like)
    session.commit()

    return {"message": "Like removed successfully"}