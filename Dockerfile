# Multi-stage build for optimized CVGen image
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

# Install all dependencies in builder stage
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e ".[api]" && \
    pip install --no-cache-dir \
    pyzmq>=25.0 \
    qdrant-client>=2.7 \
    httpx>=0.27 \
    pydantic>=2.0 \
    pydantic-settings>=2.0

# Runtime stage - slim image with only necessary files
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 cvgen && \
    mkdir -p /app/data && \
    chown -R cvgen:cvgen /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=cvgen:cvgen --from=builder /build/src src/
COPY --chown=cvgen:cvgen README.md LICENSE ./

# Switch to non-root user
USER cvgen

# Expose API port
EXPOSE 8000

# Data directory for SQLite database and logs
VOLUME ["/app/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the API server
CMD ["uvicorn", "cvgen.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
