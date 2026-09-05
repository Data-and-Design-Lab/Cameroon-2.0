from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# 1. Input Schemas
# --------------------------------------------------------------------------

class ClaimInput(BaseModel):
    """
    High-level openIMIS claim schema.
    Matches standard fields present in openIMIS claim submission.
    """
    claim_id: Optional[str] = Field(default=None, description="Optional claim identifier / tracking code")
    
    # Financials & Dates
    claimed_amount: float = Field(..., ge=0, description="Total amount claimed in FCFA")
    date_from: date = Field(..., description="Service start date (YYYY-MM-DD)")
    date_to: date = Field(..., description="Service end date (YYYY-MM-DD)")
    date_claimed: Optional[date] = Field(default=None, description="Submission date to openIMIS (defaults to date_to)")
    
    # Care & Visit Type
    care_type: str = Field(default="OPD", description="Care type: OPD (Outpatient), IPD (Inpatient), UNK")
    visit_type: str = Field(default="O", description="Visit type: O (Ordinary), E (Emergency), R (Referral), UNK")
    has_explanation: Optional[bool] = Field(default=False, description="Whether claim has textual justification attached")
    
    # Health Facility (Provider)
    hfid: int = Field(default=404, description="openIMIS Health Facility ID")
    hf_level: str = Field(default="H", description="Facility level: H (Hospital), C (Health Center), D (Dispensary)")
    hf_caretype: str = Field(default="B", description="Facility care type: B (Basic), O (Other)")
    hf_legalform: str = Field(default="G", description="Facility legal form: G (Government), P (Private), D (Faith-based), C (Community)")
    geo_region: str = Field(default="Centre", description="Region in Cameroon (e.g., Centre, Littoral, Nord)")
    geo_district: str = Field(default="Guider", description="Health district name")
    
    # Diagnosis
    icdid: int = Field(default=1931, description="Primary ICD diagnosis ID")
    dx_chapter: Optional[str] = Field(default="UNK", description="ICD-10 Chapter letter (e.g., A, B, J, K) or UNK")
    
    # Policy / Insurance (Point-in-Time)
    policy_start_date: Optional[date] = Field(default=None, description="Policy effective start date")
    policy_expiry_date: Optional[date] = Field(default=None, description="Policy expiration date")
    policy_enrollment_date: Optional[date] = Field(default=None, description="Insuree enrollment date")
    
    # Service Lines (Summary)
    service_lines_count: int = Field(default=1, ge=0, description="Number of service lines in the claim")
    service_asked_total: Optional[float] = Field(default=None, description="Sum of amounts billed across services (defaults to claimed_amount)")
    service_tariff_total: Optional[float] = Field(default=None, description="Sum of standard official tariffs for billed services")
    service_asked_mean: Optional[float] = Field(default=None, description="Mean service line price")
    service_asked_max: Optional[float] = Field(default=None, description="Max service line price")
    service_tariff_breaches: int = Field(default=0, ge=0, description="Number of service lines exceeding statutory tariff limits")
    service_tariff_ratio_max: Optional[float] = Field(default=None, description="Max ratio of asked price to standard tariff")
    service_tariff_ratio_mean: Optional[float] = Field(default=None, description="Mean ratio of asked price to standard tariff")
    service_n_distinct: Optional[int] = Field(default=None, description="Number of distinct service items billed")
    service_repeat_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Fraction of duplicate service lines")
    service_top_line_share: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Share of total cost in the single largest service")
    
    # Consumables / Items (Drugs, supplies)
    item_lines_count: int = Field(default=0, ge=0, description="Number of itemized medication/consumable lines")
    item_asked_total: float = Field(default=0.0, ge=0.0, description="Total amount billed for itemized medication/consumables")

    model_config = {
        "json_schema_extra": {
            "example": {
                "claim_id": "CLM-CMR-2026-0042",
                "claimed_amount": 48500.0,
                "date_from": "2026-02-10",
                "date_to": "2026-02-12",
                "date_claimed": "2026-02-15",
                "care_type": "IPD",
                "visit_type": "E",
                "has_explanation": False,
                "hfid": 404,
                "hf_level": "H",
                "hf_caretype": "B",
                "hf_legalform": "G",
                "geo_region": "Centre",
                "geo_district": "Guider",
                "icdid": 1931,
                "dx_chapter": "J",
                "policy_start_date": "2025-06-01",
                "policy_expiry_date": "2026-05-31",
                "policy_enrollment_date": "2025-05-15",
                "service_lines_count": 4,
                "service_asked_total": 48500.0,
                "service_tariff_total": 35000.0,
                "service_asked_mean": 12125.0,
                "service_asked_max": 28000.0,
                "service_tariff_breaches": 2,
                "service_tariff_ratio_max": 1.75,
                "service_tariff_ratio_mean": 1.38,
                "service_n_distinct": 4,
                "service_repeat_rate": 0.0,
                "service_top_line_share": 0.577,
                "item_lines_count": 2,
                "item_asked_total": 12000.0
            }
        }
    }


class RawFeaturesInput(BaseModel):
    """
    Direct 51-feature vector for batch pipelines and advanced ML clients.
    """
    claim_id: Optional[str] = None
    features: Dict[str, Any] = Field(..., description="Dictionary containing the 51 features")


class BatchClaimRequest(BaseModel):
    claims: List[ClaimInput]


# --------------------------------------------------------------------------
# 2. Output & Explanation Schemas
# --------------------------------------------------------------------------

class TopFeatureContribution(BaseModel):
    feature: str = Field(..., description="Feature variable name")
    display_name: str = Field(..., description="Human-readable feature description")
    value: Any = Field(..., description="Observed value for this claim")
    impact_direction: str = Field(..., description="'INCREASES_RISK' or 'DECREASES_RISK'")
    shap_importance: float = Field(..., description="Exact TreeSHAP marginal score contribution")
    explanation: str = Field(..., description="Plain-language clinical/administrative rationale")


class ShapExplanation(BaseModel):
    baseline_log_odds: float = Field(..., description="Population baseline log-odds")
    top_risk_drivers: List[TopFeatureContribution] = Field(..., description="Top factors increasing fraud/rejection likelihood")
    top_mitigating_factors: List[TopFeatureContribution] = Field(..., description="Top factors supporting claim validity")


class PredictionResult(BaseModel):
    is_flagged: bool = Field(..., description="True if raw score exceeds optimal adjudication threshold")
    risk_tier: str = Field(..., description="CRITICAL, HIGH_RISK, MODERATE_RISK, or LOW_RISK")
    fraud_risk_percentage: float = Field(..., description="Calibrated empirical probability percentage (0.0 - 100.0%)")
    raw_model_score: float = Field(..., description="Raw gradient boosted tree probability (0.0 - 1.0)")
    decision_threshold: float = Field(..., description="Trained alert threshold")
    action_recommendation: str = Field(..., description="Recommended adjudication triage action")


class ClaimPredictionResponse(BaseModel):
    claim_id: Optional[str] = None
    prediction: PredictionResult
    explanations: ShapExplanation
    latency_ms: float = Field(..., description="Inference and explanation time in milliseconds")


class BatchClaimResponse(BaseModel):
    total_claims: int
    flagged_claims: int
    results: List[ClaimPredictionResponse]
    total_latency_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    model_family: str
    roc_auc_test: float
    pr_auc_test: float
    decision_threshold: float
    num_features: int
