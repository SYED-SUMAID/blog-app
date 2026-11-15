import os
import random

from datetime import datetime, timedelta, timezone
from faker import Faker
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

fake = Faker()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing from .env")

engine = create_engine(DATABASE_URL)

TOTAL_BLOGS = 1000

with engine.begin() as connection:

    # Fetch all existing user IDs
    user_ids = connection.execute(
        text('SELECT id FROM "user"')
    ).scalars().all()

    if not user_ids:
        raise ValueError("No users found. Seed users first.")

    blogs = []

    for _ in range(TOTAL_BLOGS):

        created_at = datetime.now(timezone.utc) - timedelta(
            days=random.randint(0, 365),
            hours=random.randint(0, 23)
        )

        blogs.append({
            "title": fake.sentence(nb_words=6).rstrip("."),
            "content": fake.paragraph(nb_sentences=12),
            "author_id": random.choice(user_ids),
            "created_at": created_at
        })

    # Insert blogs
    connection.execute(
        text("""
            INSERT INTO blog
                (title, content, author_id, created_at)
            VALUES
                (:title, :content, :author_id, :created_at)
        """),
        blogs
    )

print(f"Successfully created {TOTAL_BLOGS} dummy blogs!")
print(f"Blogs created by {len(user_ids)} available users.")

engine.dispose()