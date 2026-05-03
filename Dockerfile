# Use an official Python runtime as a parent image with slim variant for smaller size
FROM python:3.11-slim

# Install only essential system dependencies
RUN apt-get update -qq \
  && apt-get install -y --no-install-recommends \
     curl \
     gcc \
     postgresql-client \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /webSchedule

# Install dependencies first (better layer caching)
COPY requirements.txt /webSchedule/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /webSchedule/

# Collect static files
RUN python3 manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Start server with optimized gunicorn settings
CMD python manage.py migrate && \
    gunicorn webSchedule.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers=4 \
    --threads=2 \
    --worker-class=gthread \
    --worker-tmp-dir=/dev/shm \
    --timeout=300 \
    --keep-alive=5 \
    --max-requests=1000 \
    --max-requests-jitter=50 \
    --log-file=- \
    --access-logfile=- \
    --error-logfile=- 
