from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, text

from app.database.connection import get_session
from app.models.blog import Blog
from app.models.user import User
from app.schemas.blog import BlogCreate, BlogResponse
from app.security.auth import get_current_user


router = APIRouter()


# Blog joined with the author's name
BLOG_SQL = """
    SELECT b.blog_id, b.title, b.content, b.author_id, u.name AS author_name
    FROM blog b
    JOIN "user" u ON u.id = b.author_id
"""


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

    return {
        "blog_id": new_blog.blog_id,
        "title": new_blog.title,
        "content": new_blog.content,
        "author_id": new_blog.author_id,
        "author_name": current_user.name
    }


# Get all blogs (newest first)
@router.get("/blogs", response_model=list[BlogResponse])
def get_all_blogs(
    session: Session = Depends(get_session)
):

    rows = session.exec(
        text(BLOG_SQL + " ORDER BY b.blog_id DESC")
    ).mappings().all()

    return [dict(row) for row in rows]


# Get one blog
@router.get("/blog/{blog_id}", response_model=BlogResponse)
def get_blog(
    blog_id: int,
    session: Session = Depends(get_session)
):

    row = session.exec(
        text(BLOG_SQL + " WHERE b.blog_id = :blog_id").bindparams(blog_id=blog_id)
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Blog not found"
        )

    return dict(row)


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