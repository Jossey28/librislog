FROM python:3.14-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev extras)
RUN uv sync --no-dev --frozen

# Copy application source
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/

# Inject version from build args (overwrites fallback in _build_info.py)
ARG APP_VERSION=v0.0.0-dev
ARG GIT_SHA=unknown
RUN echo "__version__ = \"$APP_VERSION\"" > app/_build_info.py && \
    echo "__git_sha__ = \"$GIT_SHA\"" >> app/_build_info.py

# Entrypoint: run migrations then start server
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
