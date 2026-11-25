# ParseLab: one container serves both the API and the built React interface.
#
#   docker build -t parselab .
#   docker run -p 8000:8000 parselab        → http://localhost:8000
#
# Hosts such as Render set the PORT environment variable; the server listens on it.

# ---- Stage 1: build the frontend (React + Vite) --------------------------------
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# "npm run build" also regenerates the dark theme (prebuild hook).
RUN npm run build

# ---- Stage 2: the Python engine, serving the built frontend ---------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
# main.py serves ../frontend/dist automatically when it exists.
COPY --from=frontend /app/frontend/dist frontend/dist

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 parselab && chown -R parselab /app
USER parselab

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health',timeout=4)" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
