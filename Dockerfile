# ==============================================================================
# AutoSecOps GreenSentinel: Multi-Stage Ultra-Lean Low-Carbon Container
# Optimized for Google Cloud Run & Green Software Foundation (GSF) Carbon Intensity
# ==============================================================================

# STAGE 1: Dependency Builder
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /install

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Compile wheels into wheelhouse to eliminate build tools in final image
RUN pip wheel --no-cache-dir --wheel-dir=/install/wheels -r requirements.txt


# STAGE 2: Ultra-Lean Low-Carbon Runtime Image
FROM python:3.11-slim AS runner

# Annotations for OCI compliance & carbon transparency
LABEL maintainer="AutoSecOps GreenSentinel Core Team" \
      org.opencontainers.image.title="AutoSecOps GreenSentinel" \
      org.opencontainers.image.description="Autonomous DevSecOps Orchestrator with Real-Time SCI Carbon Metric Engine" \
      org.opencontainers.image.vendor="GitLab Transcend Hackathon 2026" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    APP_HOME=/app \
    PYTHONPATH=/app

WORKDIR ${APP_HOME}

# Copy compiled wheels from builder and install
COPY --from=builder /install/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Create unprivileged service user for DevSecOps governance compliance
RUN groupadd -g 10001 greensentinel && \
    useradd -u 10001 -g greensentinel -s /sbin/nologin -d ${APP_HOME} greensentinel

# Copy application artifacts and dashboard
COPY --chown=greensentinel:greensentinel app/ ${APP_HOME}/app/
COPY --chown=greensentinel:greensentinel agent_mcp/ ${APP_HOME}/agent_mcp/
COPY --chown=greensentinel:greensentinel scripts/ ${APP_HOME}/scripts/
COPY --chown=greensentinel:greensentinel dashboard/ ${APP_HOME}/dashboard/

# Switch to unprivileged execution context
USER greensentinel:greensentinel

# Health check tailored for Cloud Run and local orchestration
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()" || exit 1

EXPOSE 8080

# Cloud Run invokes $PORT dynamically
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
