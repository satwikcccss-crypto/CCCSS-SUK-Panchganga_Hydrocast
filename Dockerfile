# syntax=docker/dockerfile:1.7
# ==============================================================================
# HydroCast Backend — Multi-Stage Production Image
# ------------------------------------------------------------------------------
# Runtime: Python 3.12 + OpenJDK 17 JRE + GDAL/eccodes + HEC-DSS (pydsstools)
#
# Targets
#   (default)  hydrocast-backend:latest   production FastAPI service  [runner]
#   docs       MkDocs Material site build (--strict, emits /app/site)
#   dev        runtime + linters/testers/JupyterLab, drops into bash
#
# Build
#   docker build -t hydrocast-backend:2.0.0 .
#   docker build --target docs -t hydrocast-docs .
#   docker build --target dev  -t hydrocast-dev  .
#   docker buildx build --platform linux/amd64,linux/arm64 --push \
#       --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
#       -t ghcr.io/satwikcccss-crypto/hydrocast-backend:2.0.0 .
# ==============================================================================

ARG PYTHON_IMAGE=python:3.12-slim-bookworm


# ── Stage: base ───────────────────────────────────────────────────────────────
# Shared interpreter configuration. Every target derives from this one
# auditable definition of the runtime environment.
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# A relocatable venv keeps the interpreter, console scripts and site-packages in
# a single directory, so the runtime stage can copy one tree verbatim instead of
# juggling PYTHONPATH shims.
RUN python -m venv "${VIRTUAL_ENV}" && \
    pip install --upgrade pip


# ── Stage: builder ────────────────────────────────────────────────────────────
# Compiles the wheel set against GDAL/eccodes/libpq headers and a full JDK.
# Nothing from this stage (compilers, headers, apt lists) reaches the runtime.
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        openjdk-17-jdk-headless \
        libgdal-dev \
        gdal-bin \
        libpq-dev \
        libeccodes-dev \
        libeccodes-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt && pip check


# ── Stage: runner (default target) ────────────────────────────────────────────
FROM base AS runner

ARG PYTHON_IMAGE
ARG APP_VERSION=2.0.0
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="HydroCast Panchganga Flood Forecasting Backend" \
      org.opencontainers.image.description="Rainfall-runoff, river hydraulics and IoT telemetry API for the Panchganga Basin, Kolhapur." \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.vendor="CCCSS, Shivaji University Kolhapur" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.documentation="https://satwikcccss-crypto.github.io/CCCSS-SUK-Panchganga_Hydrocast/" \
      org.opencontainers.image.source="https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast" \
      org.opencontainers.image.base.name="${PYTHON_IMAGE}"

# Runtime-only shared libraries: JRE 17 (pydsstools shells out to `java`), GDAL
# with its GEOS/PROJ chain, the PostgreSQL client lib, eccodes for GRIB decoding,
# libgomp1/libgfortran5 for the SciPy wheel, curl for HEALTHCHECK, tini as PID 1.
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        libgdal32 \
        gdal-bin \
        libpq5 \
        libeccodes0 \
        libgomp1 \
        libgfortran5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    GDAL_DATA=/usr/share/gdal \
    PYTHONPATH=/app

COPY --from=builder /opt/venv /opt/venv

# Dedicated non-root account (uid/gid 1000) — the service never runs as root.
RUN groupadd --gid 1000 hydrocast && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash hydrocast

WORKDIR /app

# Application source, the versioned HEC-HMS basin project and the PostGIS schema.
COPY --chown=hydrocast:hydrocast src/ /app/src/
COPY --chown=hydrocast:hydrocast data/ /app/data/
COPY --chown=hydrocast:hydrocast database/ /app/database/

# Writable state. Only these paths are mounted as volumes in docker-compose, so
# the static inputs baked in above are never shadowed by a volume mount.
RUN mkdir -p \
        /app/data/archives \
        /app/data/raw \
        /app/data/logs \
        /app/data/observed_rainfall \
        /app/frontend/public/data/runs \
    && chown -R hydrocast:hydrocast /app

USER hydrocast

EXPOSE 8000
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS --max-time 4 "http://localhost:${PORT:-8000}/api/v1/health" || exit 1

# tini reaps zombies and forwards SIGTERM to the server. `exec` inside the shell
# makes uvicorn — not the shell — the process that receives the stop signal, so
# in-flight forecast requests finish during `docker stop`.
#
# FORWARDED_ALLOW_IPS defaults to loopback on purpose: slowapi rate-limits by
# client IP, so trusting every proxy would let a caller spoof X-Forwarded-For and
# bypass its quota. Set it to the load balancer address when one sits in front.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout-graceful-shutdown ${GRACEFUL_TIMEOUT:-30} --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]


# ── Stage: docs ───────────────────────────────────────────────────────────────
# MkDocs Material site. mkdocstrings reads src/ statically, so the hydrology
# wheels are unnecessary and this stage stays small.
FROM base AS docs

COPY requirements-docs.txt ./
RUN pip install -r requirements-docs.txt && pip check

WORKDIR /app
COPY mkdocs.yml ./
COPY docs/ /app/docs/
COPY src/ /app/src/

# --strict promotes broken anchors, missing nav entries and unresolved
# mkdocstrings identifiers to build failures, so a bad docs change cannot reach
# gh-pages. `site_dir` in mkdocs.yml resolves to /app/site.
RUN mkdocs build --strict

EXPOSE 8001
CMD ["mkdocs", "serve", "--dev-addr", "0.0.0.0:8001"]


# ── Stage: dev ────────────────────────────────────────────────────────────────
# Runtime image plus linters, type checker, test runner and JupyterLab, with the
# same non-root account and writable state as production.
FROM runner AS dev

USER root
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt && pip check
USER hydrocast

ENV JUPYTER_TOKEN=${JUPYTER_TOKEN:-hydrocast-dev} \
    MPLCONFIGDIR=/app/data/logs/matplotlib

EXPOSE 8000 8888
HEALTHCHECK NONE

CMD ["bash"]
