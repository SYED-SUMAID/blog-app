FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Prevent Python from generating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Display Python logs immediately
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create directory for persistent SQLite database
RUN mkdir -p /app/data

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "mainwithauthentication:app", "--host", "0.0.0.0", "--port", "8000"]