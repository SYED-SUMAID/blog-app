services:

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile

    container_name: blog-backend

    ports:
      - "8000:8000"

    env_file:
      - .env

    depends_on:
      db:
        condition: service_healthy

    volumes:
      - ./backend:/app

    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

    restart: unless-stopped


  # PostgreSQL Database
  db:
    image: postgres:17-alpine

    container_name: blog-database

    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

    ports:
      - "5432:5432"

    volumes:
      - postgres_data:/var/lib/postgresql/data

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

    restart: unless-stopped


  # Frontend
  frontend:
    image: nginx:alpine

    container_name: blog-frontend

    ports:
      - "5500:80"

    volumes:
      - ./frontend:/usr/share/nginx/html:ro

    restart: unless-stopped


volumes:
  postgres_data: