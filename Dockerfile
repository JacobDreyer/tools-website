# Field Kit — dynamic site: Vue frontend built with Node, served by the FastAPI
# tool server. Two stages: build the SPA, then a slim Python runtime that serves
# both the built assets and the /api that runs the tools.
#
# Base image tags verified against endoflife.date on 2026-07-24:
#   node:24-alpine   — Active LTS; the build this repo was validated on
#   python:3.14-slim — current stable; the runtime this repo was validated on

# ---------- 1. build the frontend ----------
FROM node:24-alpine AS frontend
WORKDIR /app/frontend

# copy manifests first so `npm ci` is cached until dependencies actually change
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build          # -> /app/frontend/dist

# ---------- 2. python runtime ----------
FROM python:3.14-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/ ./server/
COPY --from=frontend /app/frontend/dist ./frontend/dist

# drop root — uvicorn binds an unprivileged port (80 would need root)
RUN useradd --system --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

# the deploy smoke test and Uptime Kuma hit /healthz too; this keeps the
# container's own view of health consistent with theirs
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').read()==b'ok' else 1)"

CMD ["python", "-m", "uvicorn", "app:app", \
     "--app-dir", "server", "--host", "0.0.0.0", "--port", "8000"]
