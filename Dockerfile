# MTBirb single-origin production image.
#
# One container serves both the API and the built PWA from the same origin, so the frontend's
# `/api` contract works with no reverse-proxy or CORS layer (see backend/app/main.py). Stage 1
# builds the React/Vite bundle; stage 2 installs the FastAPI backend and copies that bundle in,
# pointing FRONTEND_DIST at it. Migrations run on start via docker-entrypoint.sh.

# ---- Stage 1: build the frontend ----
FROM node:20-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # -> /frontend/dist

# ---- Stage 2: backend runtime that also serves the built PWA ----
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the backend package. psycopg[binary] bundles libpq and shapely's wheels bundle GEOS,
# so no extra apt packages are needed on slim.
COPY backend/ ./backend/
# BirdNET sound-ID is heavy (tflite-runtime + librosa) and optional - the /api/birdnet endpoint
# returns 503 without it. Off by default to keep the image lean; build with
# --build-arg INSTALL_BIRDNET=true to include it.
ARG INSTALL_BIRDNET=false
RUN if [ "$INSTALL_BIRDNET" = "true" ]; then \
        pip install "./backend[birdnet]"; \
    else \
        pip install "./backend"; \
    fi

# Bring in the built SPA and tell the API where it lives (single-origin serving).
COPY --from=frontend /frontend/dist ./frontend/dist
ENV FRONTEND_DIST=/app/frontend/dist

# Run alembic + the server from the backend source tree (alembic.ini + alembic/ live here; the
# `app` package itself is installed into site-packages).
WORKDIR /app/backend
# Strip any CRLF line endings before making it executable: a Windows checkout can rewrite the
# script to CRLF, which makes the shebang `/bin/sh\r` and the container fail to start with
# "exec ./docker-entrypoint.sh: no such file or directory". (.gitattributes also pins it to LF.)
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
