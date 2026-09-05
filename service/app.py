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


def _print_submitted_claim(claim: ClaimInput, response: ClaimPredictionResponse):
    """Prints the received claim and AI adjudication result clearly to the backend console (safe for Windows cp1252)."""
    try:
        print("\n" + "=" * 80, flush=True)
        print(">> [openIMIS Backend] NEW CLAIM RECEIVED FOR AI VERIFICATION", flush=True)
        print("=" * 80, flush=True)
        print(f"  * Claim ID       : {claim.claim_id or 'N/A'}", flush=True)
        print(f"  * Claimed Amount : {claim.claimed_amount:,.2f} FCFA", flush=True)
        print(f"  * Service Dates  : {claim.date_from} -> {claim.date_to} (Submitted: {claim.date_claimed or claim.date_to})", flush=True)
        print(f"  * Care / Urgency : CareType: {claim.care_type} | VisitType: {claim.visit_type} | Explanation: {claim.has_explanation}", flush=True)
        print(f"  * Health Facility: ID: {claim.hfid} | Level: {claim.hf_level} | Region: {claim.geo_region} ({claim.geo_district})", flush=True)
        print(f"  * Diagnosis      : ICD ID: {claim.icdid} | Chapter: {claim.dx_chapter or 'UNK'}", flush=True)
        if claim.policy_start_date or claim.policy_expiry_date:
            print(f"  * Policy Window  : Start: {claim.policy_start_date or 'N/A'} | Expiry: {claim.policy_expiry_date or 'N/A'}", flush=True)
        print(f"  * Service Lines  : Count: {claim.service_lines_count} | Asked: {claim.service_asked_total or claim.claimed_amount:,.2f} FCFA | Tariff: {claim.service_tariff_total or 'N/A'} | Tariff Breaches: {claim.service_tariff_breaches}", flush=True)
        
        pred = response.prediction
        print("-" * 80, flush=True)
        
        # Show guardrail override prominently if triggered
        if response.guardrail_override:
            print(">> [GUARDRAIL OVERRIDE - MODEL BYPASSED]", flush=True)
            print("  !! BUSINESS RULE OVERRIDE ACTIVE - Claim adjudicated via safety rules !!", flush=True)
            for w in response.guardrail_warnings:
                print(f"  !! [{w.severity}] {w.code}: {w.message}", flush=True)
            print("-" * 80, flush=True)
        elif response.ood_warning:
            print(">> [OOD WARNING - INPUT OUTSIDE TRAINING DISTRIBUTION]", flush=True)
            for w in response.guardrail_warnings:
                if w.severity in ("HIGH", "MEDIUM"):
                    print(f"  ! [{w.severity}] {w.message}", flush=True)
            print("-" * 80, flush=True)
        elif response.guardrail_warnings:
            print(">> [GUARDRAIL AUDIT WARNINGS]", flush=True)
            for w in response.guardrail_warnings:
                print(f"  * [{w.severity}] {w.code}: {w.message}", flush=True)
            print("-" * 80, flush=True)
        
        print(">> [AI MODEL ADJUDICATION RESULT]", flush=True)
        status_tag = "[ALERT TRIGGERED]" if pred.is_flagged else "[AUTOMATED PASS]"
        if response.guardrail_override:
            status_tag = "[GUARDRAIL OVERRIDE]"
        print(f"  * Risk Tier      : {pred.risk_tier}  {status_tag}", flush=True)
        print(f"  * Fraud Risk %   : {pred.fraud_risk_percentage:.2f}% (Raw Score: {pred.raw_model_score * 100:.2f}%)", flush=True)
        print(f"  * Alert Cutoff   : {pred.decision_threshold * 100:.2f}% | Latency: {response.latency_ms:.2f} ms", flush=True)
        print(f"  * Recommendation : {pred.action_recommendation}", flush=True)
        
        if response.explanations.top_risk_drivers:
            print("  * Top Risk Drivers (TreeSHAP):", flush=True)
            for i, d in enumerate(response.explanations.top_risk_drivers, 1):
                print(f"      [{i}] {d.display_name} (Val: {d.value}) => +{d.shap_importance:.2f} SHAP | {d.explanation}", flush=True)
                
        if response.explanations.top_mitigating_factors:
            print("  * Top Mitigating Factors (TreeSHAP):", flush=True)
            for i, d in enumerate(response.explanations.top_mitigating_factors, 1):
                print(f"      [{i}] {d.display_name} (Val: {d.value}) => {d.shap_importance:.2f} SHAP | {d.explanation}", flush=True)
        print("=" * 80 + "\n", flush=True)
    except Exception as e:
        print(f">> [openIMIS Backend] Error printing claim summary: {e}", flush=True)


def _print_raw_features(payload: RawFeaturesInput, response: ClaimPredictionResponse):
    try:
        print("\n" + "=" * 80, flush=True)
        print(">> [openIMIS Backend] RAW 51-FEATURE VECTOR RECEIVED", flush=True)
        print("=" * 80, flush=True)
        print(f"  * Claim ID       : {payload.claim_id or 'N/A'}", flush=True)
        print(f"  * Features Count : {len(payload.features)} features provided", flush=True)
        sample_preview = dict(list(payload.features.items())[:6])
        print(f"  * Sample Features: {sample_preview}", flush=True)
        pred = response.prediction
        print("-" * 80, flush=True)
        print(f"  * Risk Tier      : {pred.risk_tier} | Fraud Risk: {pred.fraud_risk_percentage:.2f}% | Flagged: {pred.is_flagged}", flush=True)
        print(f"  * Latency        : {response.latency_ms:.2f} ms", flush=True)
        print("=" * 80 + "\n", flush=True)
    except Exception as e:
        print(f">> [openIMIS Backend] Error printing raw features summary: {e}", flush=True)


def _print_batch_summary(count: int, flagged: int, elapsed_ms: float):
    try:
        print("\n" + "=" * 80, flush=True)
        print(f">> [openIMIS Backend] BATCH EVALUATION COMPLETED: {count} claims scored", flush=True)
        print(f"  * Flagged Claims : {flagged} / {count} ({flagged/max(count,1):.1%})", flush=True)
        print(f"  * Total Latency  : {elapsed_ms:.2f} ms ({elapsed_ms/max(count,1):.2f} ms/claim)", flush=True)
        print("=" * 80 + "\n", flush=True)
    except Exception as e:
        print(f">> [openIMIS Backend] Error printing batch summary: {e}", flush=True)


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
        response = engine.score_claim(claim)
        _print_submitted_claim(claim, response)
        return response
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
        response = engine.score_raw_features(payload.features, claim_id=payload.claim_id)
        _print_raw_features(payload, response)
        return response
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
    _print_batch_summary(len(results), flagged, elapsed)
    
    return BatchClaimResponse(
        total_claims=len(results),
        flagged_claims=flagged,
        results=results,
        total_latency_ms=round(elapsed, 2),
    )
