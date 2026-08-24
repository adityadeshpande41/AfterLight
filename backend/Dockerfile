FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file first for caching
COPY pyproject.toml .

# Install Python dependencies including psycopg2-binary
RUN pip install --no-cache-dir . && pip install --no-cache-dir psycopg2-binary

# Copy application code
COPY . .

# Run migrations and start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
