# Backend Dockerfile for Welyne One (Agent A8)
# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (necessary for psycopg2 & other libs), plus
# Tesseract OCR (répli OCR A3 pour CV scannés, §6-A3 : "fra+eng+ara") — le
# package Python pytesseract (requirements.txt) n'est qu'un wrapper : sans le
# binaire système + packs de langue, tout appel plante à l'exécution.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    make \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
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