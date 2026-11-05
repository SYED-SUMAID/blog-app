from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database.connection import get_session
from app.models.blog import Blog
from app.models.user import User
from app.schemas.blog import BlogCreate, BlogResponse
from app.security.auth import get_current_user


router = APIRouter()


# Create a blog
@router.post("/blog", response_model=BlogResponse, status_code=201)
def create_blog(
    blog_data: BlogCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):

    new_blog = Blog(
        title=blog_data.title,
        content=blog_data.content,
        author_id=current_user.id
    )

    session.add(new_blog)
    session.commit()
    session.refresh(new_blog)

    return new_blog


# Get all blogs
@router.get("/blogs", response_model=list[BlogResponse])
def get_all_blogs(
    session: Session = Depends(get_session)
):

    blogs = session.exec(
        select(Blog)
    ).all()

    return blogs


# Get one blog
@router.get("/blog/{blog_id}", response_model=BlogResponse)
def get_blog(
    blog_id: int,
    session: Session = Depends(get_session)
):

    blog = session.get(Blog, blog_id)

    if not blog:
        raise HTTPException(
            status_code=404,
            detail="Blog not found"
        )

    return blog


# Delete a blog
@router.delete("/blog/{blog_id}")
def delete_blog(
    blog_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):

    blog = session.get(Blog, blog_id)

    if not blog:
        raise HTTPException(
            status_code=404,
            detail="Blog not found"
        )

    if blog.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete another user's blog"
        )

    session.delete(blog)
    session.commit()

    return {"message": "Blog deleted successfully"}