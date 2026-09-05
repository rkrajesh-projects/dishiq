FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
# Added g++, make, and python3-dev to prevent compilation errors (exit code 2)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# The docker-compose context for backend is '.' (root) so we can access the ml/ directory.
# All COPY paths must be relative to the root directory.

# 1. Install dependencies
COPY backend/requirements.txt .
# Upgrade pip, setuptools, and wheel to ensure manylinux wheels are properly recognized
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 2. Copy the ML directory
COPY ml /ml

# 3. Copy the backend application
COPY backend /app

ENV PYTHONPATH=/app:/ml

# 4. Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

CMD ["/app/docker-entrypoint.sh"]
