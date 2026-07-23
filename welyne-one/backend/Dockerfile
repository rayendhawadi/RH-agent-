# Backend Dockerfile for Welyne One (Agent A8)
# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (necessary for psycopg2 & other libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Default command runs Uvicorn; Celery workers are launched via docker‑compose overrides
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
