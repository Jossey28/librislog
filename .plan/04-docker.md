# LibrisLog — Docker & Deployment Plan

## Overview

Three Docker containers managed by Docker Compose:

| Service | Image | Purpose |
|---------|-------|---------|
| `traefik` | `traefik:v3` | Reverse proxy, routes traffic to backend or frontend |
| `backend` | Custom Python image | FastAPI via uvicorn |
| `frontend` | Custom nginx image | Serves static SvelteKit build (no proxy logic) |

A named volume persists the SQLite database file across container restarts.

Traefik reads routing rules from Docker labels on the `backend` and `frontend` services.
No Traefik config files are needed beyond the minimal CLI flags in the compose file.

```
Browser → :80 → Traefik ─── /api/* ──→ backend:8000
                         └── /*    ──→ frontend:80
```

No CORS issues: the browser always talks to a single origin (Traefik on port 80).

---

## backend/Dockerfile

Multi-stage is not required for Python; a single slim stage is sufficient.

```dockerfile
FROM python:3.12-slim

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

# Entrypoint: run migrations then start server
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
```

### backend/entrypoint.sh

```bash
#!/bin/sh
set -e
uv run alembic upgrade head
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## frontend/Dockerfile

Two-stage: Node build → nginx serve (static files only, no proxy config).

```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### frontend/nginx.conf

nginx only serves static files. Routing to the backend is Traefik's responsibility.

```nginx
server {
    listen 80;

    root /usr/share/nginx/html;
    index 200.html;

    # SPA fallback: all non-file routes served by 200.html
    location / {
        try_files $uri $uri/ /200.html;
    }
}
```

---

## docker-compose.yml

```yaml
services:
  traefik:
    image: traefik:v3
    command:
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --entrypoints.web.address=:80
    ports:
      - "80:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped

  backend:
    build: ./backend
    env_file: .env
    volumes:
      - db_data:/app/data
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=PathPrefix(`/api`)"
      - "traefik.http.routers.backend.entrypoints=web"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"

  frontend:
    build: ./frontend
    restart: unless-stopped
    depends_on:
      - backend
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=PathPrefix(`/`)"
      - "traefik.http.routers.frontend.entrypoints=web"
      - "traefik.http.services.frontend.loadbalancer.server.port=80"
      # Lower priority than backend so /api/ is matched first
      - "traefik.http.routers.frontend.priority=1"
      - "traefik.http.routers.backend.priority=10"

volumes:
  db_data:
```

Notes:
- `exposedbydefault=false` means only services with `traefik.enable=true` are routed.
- The `backend` router has higher priority (10) than `frontend` (1) so `/api/` routes are matched first.
- No ports are exposed on `backend` or `frontend` directly — all traffic enters via Traefik.
- `db_data` volume is mounted at `/app/data/`. `DATABASE_URL` points to `sqlite:///./data/librislog.db`.
- The Docker socket is mounted read-only so Traefik can discover containers.

---

## .env.example

```dotenv
# Backend settings
DATABASE_URL=sqlite:///./data/librislog.db
GOOGLE_BOOKS_API_KEY=        # optional, leave empty to skip Google Books
CORS_ORIGINS=["http://localhost"]
```

Copy to `.env` and fill in values. `.env` is git-ignored.

---

## Build & Run

```bash
# First time / after changes
docker compose build

# Start
docker compose up -d

# View logs
docker compose logs -f

# Traefik routing overview (optional dashboard, dev only)
# Add --api.insecure=true to traefik command, then visit http://localhost:8080

# Stop
docker compose down

# Wipe database (destroys volume!)
docker compose down -v
```

---

## Development vs Production

| Concern | Development | Production (Docker) |
|---------|-------------|---------------------|
| API base URL | `http://localhost:8000` (Vite proxy) | Same origin via Traefik `/api` route |
| CORS | Configured in FastAPI (`localhost:5173`) | Not needed (same origin) |
| Frontend | `npm run dev` (hot reload) | nginx serving static build via Traefik |
| Backend | `uv run uvicorn ... --reload` | uvicorn without `--reload` |
| DB location | `./backend/data/librislog.db` | Docker named volume |
| Routing config | Vite `server.proxy` in `vite.config.ts` | Traefik Docker labels |
