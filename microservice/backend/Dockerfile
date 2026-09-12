# ------------------------------------------------------------------------------
# Cameroon openIMIS Claim Fraud & Rejection Prediction Microservice
#
# Build from the repository root, because the image needs both the service code
# (microservice/backend/service) and the trained artifacts (models/):
#   docker build -f microservice/backend/Dockerfile -t openimis-claim-fraud-service .
# ------------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRAUD_API_MODEL_DIR=/app/models/model_lightgbm_no_leakage

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY microservice/backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn pydantic-settings httpx

# Copy service code and the serving model artifacts
COPY microservice/backend/service/ ./service/
COPY models/model_lightgbm_no_leakage/ ./models/model_lightgbm_no_leakage/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
