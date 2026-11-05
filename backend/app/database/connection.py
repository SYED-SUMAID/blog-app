import os

from sqlmodel import SQLModel, create_engine, Session


# Get the backend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Create database directory
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Database file location
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'blog.db')}"


# Create database engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# Create database tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Database session dependency
def get_session():
    with Session(engine) as session:
        yield session