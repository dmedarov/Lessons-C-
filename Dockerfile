# syntax=docker/dockerfile:1

ARG PYTHON_BUILDER_IMAGE=cgr.dev/chainguard/python:latest-dev
ARG PYTHON_RUNTIME_IMAGE=cgr.dev/chainguard/python:latest

FROM ${PYTHON_BUILDER_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

USER 0

COPY requirements.txt .
RUN python -m pip install --target /install -r requirements.txt \
    && mkdir -p /data

FROM ${PYTHON_RUNTIME_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/vendor"

WORKDIR /app

COPY --from=builder --chown=10001:10001 /install /app/vendor
COPY --from=builder --chown=10001:10001 /data /data
COPY --chown=10001:10001 app.py bootstrap_tokens.py config.py container_entrypoint.py db.py notifications_service.py rate_limit.py security.py schemas.py ./
COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 alembic ./alembic
COPY --chown=10001:10001 routers ./routers
COPY --chown=10001:10001 static ./static
COPY --chown=10001:10001 templates ./templates

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["/usr/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]

CMD ["container_entrypoint.py"]
