"""
TreeSHAP Explanation Engine for openIMIS Claim Fraud & Rejection.
Converts raw Shapley marginal contributions into actionable, plain-language clinical
and administrative reasons for medical auditors and claims adjudicators.
"""

from typing import Any, Dict, List, Tuple
from service.schemas import TopFeatureContribution

# Lazy import to avoid circular dependency
_feature_bounds = None

def _get_feature_bounds():
    """Lazy-loads FEATURE_BOUNDS to avoid circular imports."""
    global _feature_bounds
    if _feature_bounds is None:
        from service.guardrails import FEATURE_BOUNDS
        _feature_bounds = FEATURE_BOUNDS
    return _feature_bounds

FEATURE_META: Dict[str, Dict[str, str]] = {
    "POL_days_to_expiry": {
        "name": "Days to Policy Expiry",
        "pos": "Policy was expired or within immediate expiration window at service date",
        "neg": "Policy had ample active coverage remaining",
    },
    "CLM_vs_tariff_total": {
        "name": "Tariff Mark-up Ratio",
        "pos": "Claimed amount significantly exceeds official national fee schedule",
        "neg": "Claimed amount strictly aligns with standard statutory tariff",
    },
    "CLM_cost_per_day": {
        "name": "Cost Per Day",
        "pos": "Daily medical expenditure is abnormally elevated for this treatment type",
        "neg": "Daily expenditure is within standard peer benchmarks",
    },
    "SVC_tariff_breaches": {
        "name": "Tariff Ceiling Violations",
        "pos": "Multiple service line items were billed above maximum permitted rates",
        "neg": "All service items complied with legal price ceilings",
    },
    "POL_days_since_start": {
        "name": "Days Since Policy Start",
        "pos": "Claim filed immediately after policy activation (adverse selection indicator)",
        "neg": "Patient has established coverage history with no adverse selection signal",
    },
    "FLAG_policy_expired": {
        "name": "Expired Policy Flag",
        "pos": "Service was rendered after patient's insurance policy had expired",
        "neg": "Insurance policy was fully valid at time of care",
    },
    "FLAG_claim_within_30d_of_start": {
        "name": "New Policy Utilization",
        "pos": "High-cost treatment requested within 30 days of insurance signup",
        "neg": "Service requested well after initial enrollment waiting period",
    },
    "CLM_header_line_gap": {
        "name": "Header vs Lines Discrepancy",
        "pos": "Header total does not match the sum of itemized service lines",
        "neg": "Financial reconciliation between header and service lines is exact",
    },
    "SVC_tariff_ratio_max": {
        "name": "Peak Tariff Ratio",
        "pos": "Individual service line has extreme tariff markup",
        "neg": "Service tariffs are within acceptable variance thresholds",
    },
    "CLM_delay": {
        "name": "Claim Submission Delay",
        "pos": "Abnormal delay between discharge and electronic submission to openIMIS",
        "neg": "Claim was submitted promptly following clinical discharge",
    },
    "Hfid": {
        "name": "Provider Facility Profile",
        "pos": "Health facility has an elevated historical claim rejection/dispute rate",
        "neg": "Health facility maintains strong historical audit compliance",
    },
    "Icdid": {
        "name": "Diagnosis Code",
        "pos": "Diagnosis code correlates with high historical review/disallowance rates",
        "neg": "Diagnosis code has standard adjudication acceptance history",
    },
    "DX_chapter": {
        "name": "ICD-10 Disease Chapter",
        "pos": "Disease chapter billing patterns exhibit elevated audit scrutiny",
        "neg": "Routine diagnosis category with low rejection frequency",
    },
    "FLAG_backdated": {
        "name": "Backdated Submission",
        "pos": "Claim submission timestamp is backdated relative to discharge date",
        "neg": "Chronologically consistent claim submission timing",
    },
    "FLAG_no_service_lines": {
        "name": "Missing Service Details",
        "pos": "Claim header contains no itemized service breakdown",
        "neg": "Itemized service lines are fully populated",
    },
    "SVC_repeat_rate": {
        "name": "Duplicate Services Ratio",
        "pos": "Multiple identical service line entries detected on the same claim",
        "neg": "No abnormal service duplication detected",
    },
    "SVC_top_line_share": {
        "name": "Cost Concentration",
        "pos": "Disproportionate percentage of total claim concentrated in one service",
        "neg": "Balanced cost distribution across billed services",
    },
    "CLM_claimed": {
        "name": "Total Claim Amount",
        "pos": "Total claimed reimbursement is unusually high",
        "neg": "Total claim reimbursement is low to moderate",
    },
    "CLM_los": {
        "name": "Length of Stay",
        "pos": "Length of hospitalization deviates from clinical expectations",
        "neg": "Hospitalization length is consistent with clinical episode",
    },
    "FLAG_round_amount": {
        "name": "Round Number Billing",
        "pos": "Claimed amount is a rounded thousands figure (potential flat-fee estimate)",
        "neg": "Specific itemized currency total rather than round estimate",
    },
    "FLAG_weekend": {
        "name": "Weekend Service Flag",
        "pos": "Elective service scheduled on weekend",
        "neg": "Standard weekday service scheduling",
    },
}


def _format_value(val: Any) -> Any:
    """Formats float/numpy types for clean JSON output."""
    if val is None or (isinstance(val, float) and (val != val)):
        return "N/A"
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val.is_integer():
            return int(val)
        if isinstance(val, float):
            return round(val, 2)
    return str(val)
def _is_value_extreme(feat: str, val: Any) -> bool:
    """
    Checks if a feature value is far beyond the training distribution.
    Returns True if the value exceeds the training maximum by 10x or more.
    """
    bounds = _get_feature_bounds()
    if feat not in bounds or val is None:
        return False
    try:
        val_f = float(val)
    except (ValueError, TypeError):
        return False
    return abs(val_f) > bounds[feat].train_max * 10


def _get_ood_override_explanation(feat: str, val: Any, direction: str) -> str:
    """
    Returns context-aware explanation when a value is far outside training distribution.
    This overrides the static pos/neg text to prevent misleading explanations.
    """
    bounds = _get_feature_bounds()
    if feat not in bounds:
        return None
    try:
        val_f = float(val)
    except (ValueError, TypeError):
        return None

    b = bounds[feat]
    if abs(val_f) <= b.train_max:
        return None

    multiplier = abs(val_f) / b.train_max if b.train_max > 0 else float('inf')

    if direction == "neg":  # Model says this DECREASES risk — but value is extreme
        return (
            f"WARNING: {b.name} ({val_f:,.0f} {b.unit}) is {multiplier:,.0f}x the training "
            f"maximum ({b.train_max:,.0f} {b.unit}). The model's assessment is UNRELIABLE "
            f"for this value — tree-based models cannot extrapolate beyond training data. "
            f"This feature's SHAP contribution should NOT be trusted."
        )
    else:  # Model says this INCREASES risk — still flag as OOD but less contradictory
        return (
            f"{b.name} ({val_f:,.0f} {b.unit}) is {multiplier:,.0f}x the training maximum "
            f"({b.train_max:,.0f} {b.unit}). Value is far outside model's training range."
        )



def generate_explanations(
    feature_names: List[str],
    shap_values: List[float],
    feature_values: Dict[str, Any],
    top_k: int = 4,
) -> Tuple[List[TopFeatureContribution], List[TopFeatureContribution]]:
    """
    Parses TreeSHAP marginal contributions into top risk drivers and top mitigating factors.
    """
    positive_drivers: List[Tuple[str, float]] = []
    negative_drivers: List[Tuple[str, float]] = []
    
    for feat, shap_val in zip(feature_names, shap_values):
        if shap_val > 0.01:
            positive_drivers.append((feat, float(shap_val)))
        elif shap_val < -0.01:
            negative_drivers.append((feat, float(shap_val)))
            
    # Sort by absolute impact
    positive_drivers.sort(key=lambda x: x[1], reverse=True)
    negative_drivers.sort(key=lambda x: x[1])  # most negative first
    
    top_pos: List[TopFeatureContribution] = []
    for feat, shap_val in positive_drivers[:top_k]:
        meta = FEATURE_META.get(feat, {
            "name": feat.replace("_", " ").title(),
            "pos": f"Feature '{feat}' elevated claim rejection risk score",
            "neg": f"Feature '{feat}' reduced claim rejection risk score",
        })
        val = feature_values.get(feat)
        explanation = meta["pos"]
        # Override with context-aware explanation if value is extreme OOD
        ood_override = _get_ood_override_explanation(feat, val, "pos")
        if ood_override:
            explanation = ood_override
        top_pos.append(
            TopFeatureContribution(
                feature=feat,
                display_name=meta["name"],
                value=_format_value(val),
                impact_direction="INCREASES_RISK",
                shap_importance=round(shap_val, 4),
                explanation=explanation,
            )
        )
        
    top_neg: List[TopFeatureContribution] = []
    for feat, shap_val in negative_drivers[:top_k]:
        meta = FEATURE_META.get(feat, {
            "name": feat.replace("_", " ").title(),
            "pos": f"Feature '{feat}' elevated claim rejection risk score",
            "neg": f"Feature '{feat}' reduced claim rejection risk score",
        })
        val = feature_values.get(feat)
        explanation = meta["neg"]
        # Override with context-aware explanation if value is extreme OOD
        ood_override = _get_ood_override_explanation(feat, val, "neg")
        if ood_override:
            explanation = ood_override
        top_neg.append(
            TopFeatureContribution(
                feature=feat,
                display_name=meta["name"],
                value=_format_value(val),
                impact_direction="DECREASES_RISK",
                shap_importance=round(shap_val, 4),
                explanation=explanation,
            )
        )
        
    return top_pos, top_neg
