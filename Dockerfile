# syntax=docker/dockerfile:1
# Production image (spec OPS-02). Build: docker build --build-arg APP_VERSION=$(git rev-parse --short HEAD) .
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so this layer is cached across code-only changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    APP_ENV=production

RUN useradd --system --uid 10001 --no-create-home dealscope
USER dealscope

# Hosts such as Render inject PORT; 8000 is the local default.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:%s/healthz' % os.environ['PORT'], timeout=4).status == 200 else 1)"

# Worker timeout matches spec §5.5 (30 s). Access logs go to stdout.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --timeout 30 --access-logfile - app:app"]
