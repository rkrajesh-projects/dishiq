FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to ensure modern wheel metadata handling and fast resolver
RUN pip install --upgrade pip

# Create non-root system user and group
RUN groupadd -r dishiq && useradd -r -g dishiq -d /app -s /sbin/nologin dishiq

# Step 1: Pre-install CPU-only PyTorch from official PyTorch CPU wheel index
RUN pip install --timeout 120 --retries 10 \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    torch

# Step 2: Install heavy data science libraries in their own cached layer
RUN pip install --timeout 120 --retries 10 \
    "numpy>=1.22.0" \
    "pandas>=2.0.0,<3.0.0" \
    "scipy>=1.8.0" \
    "scikit-learn>=1.2.0,<2.0.0" \
    "joblib>=1.2.0,<2.0.0"

# Step 3: Install sentence-transformers (reuses pre-installed torch & scikit-learn)
RUN pip install --timeout 120 --retries 10 \
    "sentence-transformers>=2.2.0,<4.0.0"

# Step 4: Copy requirements and install remaining web, database, and auth dependencies
COPY backend/requirements.txt .
RUN pip install --timeout 120 --retries 10 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Copy the application code and ML runtime artifacts
COPY backend/ /app/
COPY ml/ /app/ml/

# Set ownership of /app to the non-root dishiq user
RUN chown -R dishiq:dishiq /app

# Switch to non-root user
USER dishiq

# Expose backend port
EXPOSE 8001

# Health check probe
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Command to run the application with proper signal propagation
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
