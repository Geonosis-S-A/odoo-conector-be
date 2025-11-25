FROM python:3.13-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Run the application with proper SSE/streaming configuration
CMD sh -c "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port \$PORT --timeout-keep-alive 300 --timeout-graceful-shutdown 30"