import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import SQLModel, Field, Session, create_engine, select, func

# ==============================================================================
# 1. DATABASE SETUP & MIGRATION SCRIPT
# ==============================================================================

DB_FILENAME = "blog_app.db"

def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    with open("init.sql", "r") as file:
        conn.executescript(file.read())
    conn.commit()
    conn.close()

init_db()

engine = create_engine(f"sqlite:///{DB_FILENAME}", connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session


# ==============================================================================
# 2. DATABASE MODELS (SQLModel Entities)
# ==============================================================================

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    username: str = Field(unique=True, nullable=False)
    password: str = Field(nullable=False)
    email: str = Field(unique=True, nullable=False)
    bio: Optional[str] = Field(default=None)


class Blog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    author_id: int = Field(foreign_key="user.id", nullable=False)


class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str = Field(nullable=False)
    commenter_id: int = Field(foreign_key="user.id", nullable=False)
    blog_id: int = Field(foreign_key="blog.id", nullable=False)


class LikeTracker(SQLModel, table=True):
    liker_id: int = Field(foreign_key="user.id", primary_key=True)
    blog_id: int = Field(foreign_key="blog.id", primary_key=True)


class UserFollow(SQLModel, table=True):
    follower_id: int = Field(foreign_key="user.id", primary_key=True)
    followed_id: int = Field(foreign_key="user.id", primary_key=True)


# ==============================================================================
# 3. REQUEST / RESPONSE SCHEMAS
# ==============================================================================

class UserGet(SQLModel):
    id: int
    name: str
    username: str
    email: str
    bio: Optional[str] = None


class UserPut(SQLModel):
    name: str
    username: str
    password: str
    email: str
    bio: Optional[str] = None


class CommentCreate(SQLModel):
    text: str
    commenter_id: int


class CommentResponse(SQLModel):
    id: int
    text: str
    commenter_id: int
    blog_id: int


class BlogDetailResponse(SQLModel):
    id: int
    title: str
    content: str
    author_id: int
    likes_count: int
    comments_count: int


# ==============================================================================
# 4. FASTAPI APP & ROUTES
# ==============================================================================

app = FastAPI(title="Blog Backend - Iteration 2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", include_in_schema=False)
   
def home():
    return FileResponse("index.html")
# ------------------------------ USER ROUTES ----------------------------------

@app.post("/user", response_model=UserGet, status_code=status.HTTP_201_CREATED)
def createUser(user: User, session: Session = Depends(get_session)):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.get("/user", response_model=UserGet)
def getUser(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/user", response_model=UserGet)
def editUser(user_id: int, updated_user: UserPut, session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.name = updated_user.name
    db_user.username = updated_user.username
    db_user.email = updated_user.email
    db_user.password = updated_user.password
    db_user.bio = updated_user.bio

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


# ------------------------------ BLOG ROUTES ----------------------------------

@app.post("/blog", response_model=Blog, status_code=status.HTTP_201_CREATED)
def createBlog(blog: Blog, session: Session = Depends(get_session)):
    author = session.get(User, blog.author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    session.add(blog)
    session.commit()
    session.refresh(blog)
    return blog


@app.get("/blog", response_model=BlogDetailResponse)
def getBlog(blog_id: int, session: Session = Depends(get_session)):
    """US-303: Fetches a single blog with calculated likes and comments count."""
    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    likes = session.exec(select(func.count(LikeTracker.liker_id)).where(LikeTracker.blog_id == blog_id)).one()
    comments = session.exec(select(func.count(Comment.id)).where(Comment.blog_id == blog_id)).one()

    return BlogDetailResponse(
        id=blog.id,
        title=blog.title,
        content=blog.content,
        author_id=blog.author_id,
        likes_count=likes,
        comments_count=comments
    )


@app.get("/blogs", response_model=List[BlogDetailResponse])
def getAllBlogs(session: Session = Depends(get_session)):
    """US-303: Fetches all blogs, each annotated with its like and comment counts."""
    blogs = session.exec(select(Blog)).all()
    result = []
    for b in blogs:
        likes = session.exec(select(func.count(LikeTracker.liker_id)).where(LikeTracker.blog_id == b.id)).one()
        comments = session.exec(select(func.count(Comment.id)).where(Comment.blog_id == b.id)).one()
        result.append(BlogDetailResponse(
            id=b.id,
            title=b.title,
            content=b.content,
            author_id=b.author_id,
            likes_count=likes,
            comments_count=comments
        ))
    return result


@app.delete("/blog")
def deleteBlog(blog_id: int, session: Session = Depends(get_session)):
    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    session.delete(blog)
    session.commit()
    return {"message": "Blog and all associated comments/likes deleted successfully"}


# ---------------------------- COMMENT ROUTES ---------------------------------

@app.post("/blog/{blog_id}/comment", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def addComment(blog_id: int, comment_data: CommentCreate, session: Session = Depends(get_session)):
    """US-301: Add a comment to a specific blog."""
    if not session.get(Blog, blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    if not session.get(User, comment_data.commenter_id):
        raise HTTPException(status_code=404, detail="Commenter not found")

    new_comment = Comment(
        text=comment_data.text,
        commenter_id=comment_data.commenter_id,
        blog_id=blog_id
    )
    session.add(new_comment)
    session.commit()
    session.refresh(new_comment)
    return new_comment


@app.get("/blog/{blog_id}/comments", response_model=List[CommentResponse])
def getBlogComments(blog_id: int, session: Session = Depends(get_session)):
    """Fetch all comments for a blog post."""
    if not session.get(Blog, blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    return session.exec(select(Comment).where(Comment.blog_id == blog_id)).all()


# ----------------------------- LIKE ROUTES -----------------------------------

@app.post("/blog/{blog_id}/like")
def toggleLike(blog_id: int, user_id: int, session: Session = Depends(get_session)):
    """US-302: Likes a post if not liked yet; unlikes if already liked (Toggle pattern)."""
    if not session.get(Blog, blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    if not session.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    existing_like = session.get(LikeTracker, (user_id, blog_id))
    if existing_like:
        session.delete(existing_like)
        session.commit()
        return {"message": "Post unliked", "liked": False}
    else:
        new_like = LikeTracker(liker_id=user_id, blog_id=blog_id)
        session.add(new_like)
        session.commit()
        return {"message": "Post liked", "liked": True}


# ---------------------------- FOLLOW ROUTES ----------------------------------

@app.post("/user/{target_user_id}/follow")
def followUser(target_user_id: int, current_user_id: int, session: Session = Depends(get_session)):
    """US-304: Follow another user."""
    if target_user_id == current_user_id:
        raise HTTPException(status_code=400, detail="Users cannot follow themselves")
    if not session.get(User, target_user_id) or not session.get(User, current_user_id):
        raise HTTPException(status_code=404, detail="User not found")

    existing_follow = session.get(UserFollow, (current_user_id, target_user_id))
    if existing_follow:
        session.delete(existing_follow)
        session.commit()
        return {"message": f"Unfollowed user {target_user_id}", "following": False}
    else:
        new_follow = UserFollow(follower_id=current_user_id, followed_id=target_user_id)
        session.add(new_follow)
        session.commit()
        return {"message": f"Now following user {target_user_id}", "following": True}