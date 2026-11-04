import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
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
# 2. SECURITY CONFIGURATION (BCRYPT & JWT)
# ==============================================================================

SECRET_KEY = "blogsecret@123" # Used to sign token.
ALGORITHM = "HS256" #JWT Signature last part
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # 1 hour JWT expiry

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12, deprecated="auto") 
#Specify standard bcrypt $2b$ 
# with  cost factor 12
# deprecated_auto : Auto handles the deprecated versions of bcrypt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
#dependency to inspect HTTP requests for a bearerToken in HTTP Authorization header

def hash_password(password: str) -> str: #return type hint passsword: abc@123
    return pwd_context.hash(password) # hash "1223132jwdbwjhb"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str: # data ={ sub: sumaid}
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire}) # data = {sub: sumaid, exp: 32131232}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ==============================================================================
# 3. DATABASE MODELS (SQLModel Entities)
# ==============================================================================

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    username: str = Field(unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
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
# 4. REQUEST / RESPONSE SCHEMAS
# ==============================================================================

class UserCreate(SQLModel):
    name: str
    username: str
    password: str
    email: str
    bio: Optional[str] = None


class UserGet(SQLModel):
    id: int
    name: str
    username: str
    hashed_password: str
    email: str
    bio: Optional[str] = None


class UserPut(SQLModel):
    name: str
    username: str
    password: Optional[str] = None
    email: str
    bio: Optional[str] = None


class Token(SQLModel):
    access_token: str
    token_type: str


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
# 5. AUTH DEPENDENCY
# ==============================================================================

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # {Sub: sumaid, expiry:323232}
        username: Optional[str] = payload.get("sub") # sumaid
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user


# ==============================================================================
# 6. FASTAPI APP & ROUTES
# ==============================================================================

app = FastAPI(title="Blog Backend - Iteration 2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------ AUTH ROUTES ----------------------------------

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    clean_username = form_data.username.strip().lower()
    user = session.exec(select(User).where(func.lower(User.username) == clean_username)).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ------------------------------ USER ROUTES ----------------------------------

@app.post("/user", response_model=UserGet, status_code=status.HTTP_201_CREATED)
def createUser(user: UserCreate, session: Session = Depends(get_session)):
    clean_username = user.username.strip().lower()
    clean_email = user.email.strip().lower()

    if session.exec(select(User).where(func.lower(User.username) == clean_username)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken.."
        )

    if session.exec(select(User).where(func.lower(User.email) == clean_email)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.."
        )

    db_user = User(
        name=user.name.strip(),
        username=clean_username,
        email=clean_email,
        bio=user.bio,
        hashed_password=hash_password(user.password)
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@app.get("/user/me", response_model=UserGet)
def getMyProfile(current_user: User = Depends(get_current_user)):
    return current_user


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
    
    db_user.name = updated_user.name.strip()
    db_user.username = updated_user.username.strip().lower()
    db_user.email = updated_user.email.strip().lower()
    db_user.bio = updated_user.bio

    if updated_user.password:
        db_user.hashed_password = hash_password(updated_user.password)

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
    if not session.get(Blog, blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    return session.exec(select(Comment).where(Comment.blog_id == blog_id)).all()


# ----------------------------- LIKE ROUTES -----------------------------------

@app.post("/blog/{blog_id}/like")
def toggleLike(blog_id: int, user_id: int, session: Session = Depends(get_session)):
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