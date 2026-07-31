FROM python:3.11-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        fastapi uvicorn[standard] sqlalchemy argon2-cffi python-jose[cryptography] \
        stripe pydantic[email] slowapi limits psycopg2-binary \
        pyyaml networkx numpy scipy scikit-learn jinja2

COPY api/ ./api/
COPY agents/ ./agents/
COPY persona_math/ ./persona_math/
COPY persona_mcp/ ./persona_mcp/

ENV DATABASE_URL=sqlite:////app/data/persona_platform.db
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
