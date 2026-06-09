FROM python:3.11-slim

WORKDIR /app

# Non-root user for security
RUN groupadd -r persona && useradd -r -g persona persona

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy app source
COPY . .

# Install persona_math package (no additional deps needed)
RUN pip install --no-cache-dir -e . --no-deps

RUN chown -R persona:persona /app
USER persona

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2"]
