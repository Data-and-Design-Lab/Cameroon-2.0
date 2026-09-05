"""
FastAPI Microservice for openIMIS Healthcare Claim Fraud & Rejection Prediction.
Provides real-time scoring, calibrated probability percentages, and TreeSHAP explainability.
"""

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from service.config import settings
from service.engine import FraudModelEngine
from service.schemas import (
    BatchClaimRequest,
    BatchClaimResponse,
    ClaimInput,
    ClaimPredictionResponse,
    HealthResponse,
    RawFeaturesInput,
)

# Application lifespan manager to preload model on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload model artifacts into memory
    engine = FraudModelEngine.get_instance()
    app.state.engine = engine
    yield
    # Cleanup on shutdown if needed


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for browser-based dashboards and EHR frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Overview"])
def root():
    """Service landing endpoint with quick links and metadata."""
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "schema": "/api/v1/schema",
            "predict_claim": "/api/v1/predict/claim",
            "predict_features": "/api/v1/predict/features",
            "predict_batch": "/api/v1/predict/batch",
        },
        "model_performance": {
            "algorithm": "Leakage-Free LightGBM GBDT + Isotonic Regression",
            "roc_auc_test": 0.8778,
            "pr_auc_test": 0.7604,
            "precision_at_alert_threshold": "91.79%",
            "explainability": "Exact TreeSHAP attribution",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """Healthcheck endpoint for Kubernetes, Docker, and uptime monitoring."""
    engine = getattr(app.state, "engine", None) or FraudModelEngine.get_instance()
    return engine.get_health_stats()


@app.get("/api/v1/schema", tags=["Schema & Metadata"])
def get_feature_schema() -> Dict[str, Any]:
    """Returns the model's 51 features, expected categories, and sample values."""
    engine = getattr(app.state, "engine", None) or FraudModelEngine.get_instance()
    return {
        "num_features": len(engine.features),
        "features": engine.features,
        "categorical_columns": engine.cat_features,
        "sample_categories": {
            k: v[:10] if len(v) > 10 else v
            for k, v in engine.categories.items()
        },
        "decision_threshold": engine.decision_threshold,
    }


@app.post(
    "/api/v1/predict/claim",
    response_model=ClaimPredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    summary="Predict fraud & rejection risk from standard openIMIS claim fields",
)
def predict_claim(claim: ClaimInput):
    """
    Primary endpoint for openIMIS and hospital EHR software.
    
    Accepts natural claim attributes (amounts, dates, facility ID, line items summary),
    transforms them into the 51 model features, calculates the calibrated fraud probability
    percentage, and returns top TreeSHAP risk factors and mitigating factors.
    """
    try:
        engine = getattr(app.state, "engine", None) or FraudModelEngine.get_instance()
        return engine.score_claim(claim)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(exc)}",
        )


@app.post(
    "/api/v1/predict/features",
    response_model=ClaimPredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    summary="Direct prediction from 51 pre-computed model features",
)
def predict_features(payload: RawFeaturesInput):
    """
    Low-level endpoint for batch pipelines and advanced integrations where features
    are pre-computed before sending.
    """
    try:
        engine = getattr(app.state, "engine", None) or FraudModelEngine.get_instance()
        return engine.score_raw_features(payload.features, claim_id=payload.claim_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error on raw feature vector: {str(exc)}",
        )


@app.post(
    "/api/v1/predict/batch",
    response_model=BatchClaimResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    summary="Batch scoring for multiple openIMIS claims",
)
def predict_batch(request: BatchClaimRequest):
    """
    Batch endpoint for scoring dozens or hundreds of openIMIS claims in parallel.
    """
    start_t = time.perf_counter()
    engine = getattr(app.state, "engine", None) or FraudModelEngine.get_instance()
    
    results = engine.score_batch(request.claims)
    flagged = sum(1 for r in results if r.prediction.is_flagged)
    elapsed = (time.perf_counter() - start_t) * 1000.0
    
    return BatchClaimResponse(
        total_claims=len(results),
        flagged_claims=flagged,
        results=results,
        total_latency_ms=round(elapsed, 2),
    )
