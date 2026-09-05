#!/bin/bash
set -e

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Run seed script
echo "Seeding database..."
python app/db/seed.py

# Start uvicorn
echo "Starting backend server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
