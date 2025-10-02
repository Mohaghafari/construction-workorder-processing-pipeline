# Multi-stage Dockerfile for Work Order Processing Pipeline
# Base image with Python 3.12 and Poppler for PDF processing

FROM python:3.12-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpoppler-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY dbt/ ./dbt/
COPY airflow/ ./airflow/
COPY scripts/ ./scripts/
COPY utils/ ./utils/
COPY *.py ./

# Copy configuration templates
COPY .env.example ./

# Create necessary directories
RUN mkdir -p logs credentials data/exports

# Set environment variables
ENV PYTHONPATH=/app
ENV POPPLER_PATH=/usr/bin

# Default command
CMD ["python", "scripts/run_pipeline.py", "--check-only"]

# ===================================
# Development image with testing tools
# ===================================
FROM base as development

RUN pip install --no-cache-dir -r requirements-dev.txt

# Install dbt
RUN pip install --no-cache-dir dbt-bigquery==1.7.0

CMD ["/bin/bash"]

# ===================================
# Production image (minimal)
# ===================================
FROM base as production

# Remove dev dependencies
RUN pip uninstall -y pytest pytest-cov

# Set production environment
ENV ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

CMD ["python", "scripts/run_pipeline.py"]

