"""
Feature Transformation Engine for openIMIS Claim Fraud Detection.
Converts raw claim records into the exact 51-feature vector used by LightGBM.
"""

from datetime import date
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from service.schemas import ClaimInput


def _sanitize_category(val: Any, allowed_categories: List[Any]) -> Any:
    """
    Sanitizes categorical values against model-known categories.
    Falls back to 'UNK' or None if out-of-vocabulary.
    """
    if val is None or pd.isna(val):
        return "UNK" if "UNK" in allowed_categories else None
    
    # Check exact type match or string/int casting
    if val in allowed_categories:
        return val
    try:
        int_val = int(val)
        if int_val in allowed_categories:
            return int_val
    except (ValueError, TypeError):
        pass
    
    str_val = str(val).strip()
    if str_val in allowed_categories:
        return str_val
    
    # Fallback
    if "UNK" in allowed_categories:
        return "UNK"
    return None


def claim_to_feature_dict(claim: ClaimInput) -> Dict[str, Any]:
    """
    Transforms a single ClaimInput into a dictionary of 51 features.
    """
    # 1. Financials & Timing
    claimed = float(claim.claimed_amount)
    date_from = claim.date_from
    date_to = claim.date_to
    date_claimed = claim.date_claimed or date_to
    
    los = (date_to - date_from).days
    delay = (date_claimed - date_to).days
    dayofweek = date_claimed.weekday()
    month = date_claimed.month
    
    cost_per_day = claimed / max(abs(los), 1)
    
    # 2. Services & Line Items
    svc_lines = max(int(claim.service_lines_count), 0)
    cost_per_line = claimed / max(svc_lines, 1)
    
    svc_asked_total = (
        float(claim.service_asked_total)
        if claim.service_asked_total is not None
        else claimed
    )
    header_line_gap = claimed - svc_asked_total
    
    svc_tariff_total = (
        float(claim.service_tariff_total)
        if claim.service_tariff_total is not None
        else (claimed if claimed > 0 else 1.0)
    )
    clm_vs_tariff_total = claimed / svc_tariff_total if svc_tariff_total > 0 else np.nan
    
    svc_asked_mean = (
        float(claim.service_asked_mean)
        if claim.service_asked_mean is not None
        else (svc_asked_total / max(svc_lines, 1))
    )
    svc_asked_max = (
        float(claim.service_asked_max)
        if claim.service_asked_max is not None
        else svc_asked_mean
    )
    
    svc_tariff_ratio_mean = (
        float(claim.service_tariff_ratio_mean)
        if claim.service_tariff_ratio_mean is not None
        else (svc_asked_total / max(svc_tariff_total, 1.0))
    )
    svc_tariff_ratio_max = (
        float(claim.service_tariff_ratio_max)
        if claim.service_tariff_ratio_max is not None
        else svc_tariff_ratio_mean
    )
    
    svc_n_distinct = (
        int(claim.service_n_distinct)
        if claim.service_n_distinct is not None
        else svc_lines
    )
    svc_top_line_share = (
        float(claim.service_top_line_share)
        if claim.service_top_line_share is not None
        else (svc_asked_max / max(svc_asked_total, 1.0) if svc_asked_total > 0 else 0.0)
    )
    
    # 3. Item / Drug Consumables
    itm_lines = max(int(claim.item_lines_count), 0)
    itm_asked_total = float(claim.item_asked_total)
    
    # 4. Policy (Point-in-Time)
    has_policy = claim.policy_start_date is not None
    if has_policy:
        pol_days_since_start = float((date_from - claim.policy_start_date).days)
        flag_no_policy_found = 0
    else:
        pol_days_since_start = np.nan
        flag_no_policy_found = 1
        
    if claim.policy_expiry_date is not None:
        pol_days_to_expiry = float((claim.policy_expiry_date - date_from).days)
        flag_policy_expired = 1 if pol_days_to_expiry < 0 else 0
    else:
        pol_days_to_expiry = np.nan
        flag_policy_expired = 0
        
    if claim.policy_enrollment_date is not None:
        pol_days_since_enroll = float((date_from - claim.policy_enrollment_date).days)
    else:
        pol_days_since_enroll = pol_days_since_start if has_policy else np.nan
        
    flag_claim_within_30d = (
        1 if (has_policy and 0 <= pol_days_since_start <= 30) else 0
    )
    
    # 5. Rule Flags
    flag_backdated = 1 if delay < 0 else 0
    flag_has_explanation = 1 if claim.has_explanation else 0
    flag_has_item_lines = 1 if itm_lines > 0 else 0
    flag_los_over_year = 1 if los > 365 else 0
    flag_neg_claimed = 1 if claimed < 0 else 0
    flag_negative_los = 1 if los < 0 else 0
    flag_no_service_lines = 1 if svc_lines == 0 else 0
    flag_round_amount = 1 if (claimed > 0 and claimed % 1000 == 0) else 0
    flag_weekend = 1 if dayofweek in (5, 6) else 0
    isna_claimed = 0
    
    # 6. Diagnosis ICD Chapter
    dx_chap = claim.dx_chapter or "UNK"
    if len(dx_chap) > 1 and dx_chap != "UNK":
        dx_chap = dx_chap[0].upper()

    row = {
        "CLM_claimed": claimed,
        "CLM_cost_per_day": cost_per_day,
        "CLM_cost_per_line": cost_per_line,
        "CLM_dayofweek": float(dayofweek),
        "CLM_delay": float(delay),
        "CLM_header_line_gap": header_line_gap,
        "CLM_los": float(los),
        "CLM_month": float(month),
        "CLM_vs_tariff_total": clm_vs_tariff_total,
        "ITM_asked_total": itm_asked_total,
        "ITM_n_lines": float(itm_lines),
        "POL_days_since_enroll": pol_days_since_enroll,
        "POL_days_since_start": pol_days_since_start,
        "POL_days_to_expiry": pol_days_to_expiry,
        "SVC_asked_max": svc_asked_max,
        "SVC_asked_mean": svc_asked_mean,
        "SVC_asked_total": svc_asked_total,
        "SVC_freq_limit_min": 1.0,
        "SVC_n_distinct": float(svc_n_distinct),
        "SVC_n_lines": float(svc_lines),
        "SVC_patcat_nunique": 1.0,
        "SVC_qty_total": float(max(svc_lines, 1)),
        "SVC_repeat_rate": float(claim.service_repeat_rate),
        "SVC_tariff_breaches": float(claim.service_tariff_breaches),
        "SVC_tariff_ratio_max": svc_tariff_ratio_max,
        "SVC_tariff_ratio_mean": svc_tariff_ratio_mean,
        "SVC_tariff_total": svc_tariff_total,
        "SVC_top_line_share": svc_top_line_share,
        "FLAG_backdated": flag_backdated,
        "FLAG_claim_within_30d_of_start": flag_claim_within_30d,
        "FLAG_has_explanation": flag_has_explanation,
        "FLAG_has_item_lines": flag_has_item_lines,
        "FLAG_los_over_year": flag_los_over_year,
        "FLAG_neg_claimed": flag_neg_claimed,
        "FLAG_negative_los": flag_negative_los,
        "FLAG_no_policy_found": flag_no_policy_found,
        "FLAG_no_service_lines": flag_no_service_lines,
        "FLAG_policy_expired": flag_policy_expired,
        "FLAG_round_amount": flag_round_amount,
        "FLAG_weekend": flag_weekend,
        "ISNA_claimed": isna_claimed,
        "CareType": claim.care_type,
        "VisitType": claim.visit_type,
        "HF_level": claim.hf_level,
        "HF_caretype": claim.hf_caretype,
        "HF_legalform": claim.hf_legalform,
        "GEO_region": claim.geo_region,
        "GEO_district": claim.geo_district,
        "DX_chapter": dx_chap,
        "Hfid": claim.hfid,
        "Icdid": claim.icdid,
    }
    return row


def build_dataframe(
    rows: List[Dict[str, Any]],
    feature_names: List[str],
    cat_columns: List[str],
    categories: Dict[str, List[Any]],
) -> pd.DataFrame:
    """
    Constructs a validated pandas DataFrame matching LightGBM's exact schema.
    """
    df = pd.DataFrame(rows)
    
    # Ensure all required features are present
    for col in feature_names:
        if col not in df.columns:
            df[col] = np.nan
            
    # Reorder columns to match training schema precisely
    df = df[feature_names].copy()
    
    # Encode categoricals safely
    for col in cat_columns:
        allowed = categories.get(col, [])
        df[col] = df[col].apply(lambda x: _sanitize_category(x, allowed))
        df[col] = pd.Categorical(df[col], categories=allowed)
        
    return df
