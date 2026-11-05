from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import database functions
from app.database.connection import create_db_and_tables

# Import models so SQLModel knows about all tables
from app.models import User, Blog, Comment, Like, Follow

# Import route files
from app.routes import users, blogs, comments, likes, follows


# Run when the application starts
@asynccontextmanager
async def lifespan(app: FastAPI):

    create_db_and_tables()

    yield


# Create FastAPI application
app = FastAPI(
    title="Blog API",
    description="A blog application with authentication",
    version="1.0.0",
    lifespan=lifespan
)


# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routes
app.include_router(users.router)
app.include_router(blogs.router)
app.include_router(comments.router)
app.include_router(likes.router)
app.include_router(follows.router)


# Home endpoint
@app.get("/")
def home():
    return {"message": "Blog API is running"}