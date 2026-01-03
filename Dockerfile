# Stage 1: Build
FROM python:3.13-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml poetry.lock ./
COPY src/ ./src/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Install psutil dependencies (if any needed for slim, usually none)
# But nvidia-ml-py needs the drivers which are passed through

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ ./src/

EXPOSE 8000

ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "clarion.server:app", "--host", "0.0.0.0", "--port", "8000"]
