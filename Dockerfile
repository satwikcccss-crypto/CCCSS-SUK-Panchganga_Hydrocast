# ==============================================================================
# HydroCast Backend Multi-Stage Production Dockerfile
# Python 3.12 + OpenJDK 17 + GDAL/eccodes + HEC-DSS runtime
# ==============================================================================

# ── Stage 1: Build & Dependencies ─────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install C/C++ compilation tools, OpenJDK 17, and GIS/meteorological C libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    openjdk-17-jdk-headless \
    libgdal-dev \
    gdal-bin \
    libpq-dev \
    libeccodes-dev \
    libeccodes-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python packages into isolated wheels / prefix
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install -r requirements.txt


# ── Stage 2: Production Runtime ───────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH="/app/.local/bin:/install/bin:${PATH}" \
    PYTHONPATH=/app

# Install minimal shared runtime libraries (JRE 17, GDAL, eccodes, libpq, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    libgdal32 \
    gdal-bin \
    libpq5 \
    libeccodes0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Create non-root dedicated application user for security
RUN groupadd -g 1000 hydrocast && \
    useradd -u 1000 -g hydrocast -m -s /bin/bash hydrocast && \
    mkdir -p /app/data /app/data/archives /app/data/logs /app/data/openmeteo_dss && \
    chown -R hydrocast:hydrocast /app

# Copy application source code & assets
COPY --chown=hydrocast:hydrocast src/ /app/src/
COPY --chown=hydrocast:hydrocast data/ /app/data/
COPY --chown=hydrocast:hydrocast database/ /app/database/

USER hydrocast

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
