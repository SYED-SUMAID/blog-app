import os

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session


# Load environment variables from the root .env file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

PROJECT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(PROJECT_DIR, ".env"))


# Get PostgreSQL connection URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not configured")


# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# Create database tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Database session dependency
def get_session():
    with Session(engine) as session:
        yield session