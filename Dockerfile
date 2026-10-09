# Python 3.12, same as your computer. "slim" keeps the image small.
FROM python:3.12-slim

# Print logs right away (so they show up in Cloud Run) and don't write .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install packages first, so Docker can reuse this layer when only your code changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the app (everything not listed in .dockerignore)
COPY . .

# Run as a regular user instead of root (safer)
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Cloud Run tells the app which port to use through $PORT (8080 by default)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}