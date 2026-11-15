import os
import uuid
import bcrypt

from faker import Faker
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
load_dotenv()

fake = Faker()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing from .env")

engine = create_engine(DATABASE_URL)

# Generate one password hash for all test users
hashed_password = bcrypt.hashpw(
    b"Test@12345",
    bcrypt.gensalt()
).decode("utf-8")

users = []

for _ in range(500):
    unique_id = uuid.uuid4().hex[:8]

users.append({
    "name": fake.name(),
    "username": f"user_{unique_id}",
    "email": f"user_{unique_id}@example.com",
    "hashed_password": hashed_password,
    "created_at": datetime.now(timezone.utc)
})
with engine.begin() as connection:

    connection.execute(
        text("""
            INSERT INTO "user"
            (name, username, email, hashed_password, created_at)
            VALUES
            (:name, :username, :email, :hashed_password, :created_at)
        """),
        users
    )

print("Successfully added 500 dummy users!")
print("Password for all users: Test@12345")

engine.dispose()