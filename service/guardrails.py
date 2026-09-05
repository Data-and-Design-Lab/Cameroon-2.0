"""
Pre-Model Guardrails & Out-of-Distribution (OOD) Detection for openIMIS Fraud Service.

Provides defense-in-depth safety layers that operate BEFORE and AFTER the LightGBM model:
1. Input validation & plausibility checks (hard business rules)
2. Feature capping / winsorization (keeps model in-distribution)
3. Post-model tier overrides (extreme values force escalation regardless of model score)
4. OOD detection warnings (alerts when inputs are far outside training distribution)

Tree-based models (LightGBM, XGBoost, Random Forest) CANNOT extrapolate beyond
their training split boundaries. Any value above the training max lands in the same
leaf as the training max itself. This module guards against that fundamental limitation.

Training Distribution Reference (14.2M claims, Cameroon openIMIS):
  CLM_claimed: Median 2,500 | P99.9 87,100 | P99.99 120,405 | Max 500,022,000 FCFA
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("fraud_service.guardrails")


# ---------------------------------------------------------------------------
# Training Distribution Reference Bounds
# ---------------------------------------------------------------------------
# Calibrated from the 14.2M-claim Cameroon openIMIS dataset (TblClaim).
# IMPORTANT: These MUST be updated whenever the model is retrained on new data.

@dataclass(frozen=True)
class FeatureBounds:
    """Defines the plausible range for a numeric feature based on training data."""
    name: str
    p999: float           # 99.9th percentile — values above this are extreme outliers
    train_max: float      # Maximum value observed in training data
    hard_ceiling: float   # Absolute business-rule ceiling — above this → CRITICAL override
    unit: str = "FCFA"


# Bounds calibrated from actual training distribution analysis.
#
# CLM_claimed training distribution:
#   Median: 2,500 | P99: 27,045 | P99.9: 87,100 | P99.99: 120,405 | Max: 500,022,000
#
# hard_ceiling is set at a generous 10x the training max for CLM_claimed,
# and proportionally for derived features. This allows legitimate high-value
# claims while catching absurd values that would fool the model.
FEATURE_BOUNDS: Dict[str, FeatureBounds] = {
    "CLM_claimed": FeatureBounds(
        name="Total Claimed Amount",
        p999=87_100.0,
        train_max=500_022_000.0,
        hard_ceiling=5_000_000_000.0,  # 5 billion FCFA — generous 10x training max
        unit="FCFA",
    ),
    "CLM_cost_per_day": FeatureBounds(
        name="Cost Per Day",
        p999=87_100.0,         # Conservative: same as claimed P999 (1-day stay)
        train_max=500_022_000.0,
        hard_ceiling=1_000_000_000.0,
        unit="FCFA/day",
    ),
    "CLM_cost_per_line": FeatureBounds(
        name="Cost Per Service Line",
        p999=87_100.0,
        train_max=500_022_000.0,
        hard_ceiling=1_000_000_000.0,
        unit="FCFA/line",
    ),
    "CLM_header_line_gap": FeatureBounds(
        name="Header vs Lines Discrepancy",
        p999=50_000.0,
        train_max=500_000_000.0,
        hard_ceiling=1_000_000_000.0,
        unit="FCFA",
    ),
    "SVC_asked_total": FeatureBounds(
        name="Service Asked Total",
        p999=87_100.0,
        train_max=500_022_000.0,
        hard_ceiling=5_000_000_000.0,
        unit="FCFA",
    ),
    "SVC_asked_max": FeatureBounds(
        name="Service Asked Max",
        p999=60_000.0,
        train_max=100_000_000.0,
        hard_ceiling=2_000_000_000.0,
        unit="FCFA",
    ),
    "SVC_asked_mean": FeatureBounds(
        name="Service Asked Mean",
        p999=60_000.0,
        train_max=100_000_000.0,
        hard_ceiling=2_000_000_000.0,
        unit="FCFA",
    ),
    "SVC_tariff_total": FeatureBounds(
        name="Service Tariff Total",
        p999=60_000.0,
        train_max=100_000_000.0,
        hard_ceiling=2_000_000_000.0,
        unit="FCFA",
    ),
    "ITM_asked_total": FeatureBounds(
        name="Item Asked Total",
        p999=50_000.0,
        train_max=50_000_000.0,
        hard_ceiling=1_000_000_000.0,
        unit="FCFA",
    ),
    "CLM_los": FeatureBounds(
        name="Length of Stay",
        p999=60.0,
        train_max=365.0,
        hard_ceiling=730.0,  # 2 years — anything beyond is clinically implausible
        unit="days",
    ),
}

# Features that are monetary and can be capped by winsorization
MONETARY_FEATURES = [
    "CLM_claimed", "CLM_cost_per_day", "CLM_cost_per_line",
    "CLM_header_line_gap", "SVC_asked_total", "SVC_asked_max",
    "SVC_asked_mean", "SVC_tariff_total", "ITM_asked_total",
]


# ---------------------------------------------------------------------------
# Guardrail Warning Dataclass
# ---------------------------------------------------------------------------

@dataclass
class GuardrailWarning:
    """A single guardrail violation or OOD detection result."""
    code: str                   # Machine-readable code (e.g., "EXTREME_AMOUNT", "OOD_FEATURE")
    severity: str               # "CRITICAL", "HIGH", "MEDIUM", "INFO"
    feature: Optional[str]      # Which feature triggered this (if applicable)
    message: str                # Human-readable explanation
    original_value: Optional[float] = None   # The raw input value before capping
    capped_value: Optional[float] = None     # The value after winsorization (if applicable)


@dataclass
class GuardrailResult:
    """Aggregated result of all guardrail checks on a single claim."""
    warnings: List[GuardrailWarning] = field(default_factory=list)
    override_tier: Optional[str] = None          # Force this risk tier (overrides model)
    override_action: Optional[str] = None        # Force this action recommendation
    override_flagged: Optional[bool] = None      # Force flagged status
    was_capped: bool = False                      # Whether any feature was winsorized
    is_ood: bool = False                          # Whether input is outside training distribution

    @property
    def has_critical(self) -> bool:
        return any(w.severity == "CRITICAL" for w in self.warnings)

    @property
    def has_override(self) -> bool:
        return self.override_tier is not None

    def escalate_tier(self, tier: str, action: str, flagged: bool = True) -> None:
        """
        Escalates the override tier according to strict priority:
        CRITICAL (3) > HIGH_RISK (2) > MODERATE_RISK (1) > LOW_RISK (0)
        Never downgrades a higher tier to a lower tier.
        """
        priority = {"CRITICAL": 3, "HIGH_RISK": 2, "MODERATE_RISK": 1, "LOW_RISK": 0}
        current_prio = priority.get(self.override_tier or "", -1)
        new_prio = priority.get(tier, 0)

        if new_prio > current_prio:
            self.override_tier = tier
            self.override_action = action
            self.override_flagged = flagged
        elif new_prio == current_prio and self.override_action is not None:
            if action not in self.override_action:
                self.override_action = f"{self.override_action} | {action}"


# ---------------------------------------------------------------------------
# Core Guardrail Functions
# ---------------------------------------------------------------------------

def check_claim_plausibility(
    claimed_amount: float,
    cost_per_day: float,
    cost_per_line: float,
    los: float,
    feature_dict: Dict[str, Any],
    claim: Optional[Any] = None,
) -> GuardrailResult:
    """
    Runs all deterministic guardrail checks on a claim's features BEFORE model scoring.

    Provides defense-in-depth against:
    1. Extreme monetary outliers & cost-per-day ceilings
    2. Financial reconciliation failures (phantom padding, blank services)
    3. Statutory tariff gouging and excessive markups
    4. Insurance eligibility window violations (expired or pre-start care)
    5. Clinical & temporal impossibilities (negative stays, premature filings)
    6. Facility scope-of-practice mismatches

    Returns a GuardrailResult with warnings and potential tier overrides.
    """
    result = GuardrailResult()

    # =========================================================================
    # 1. Hard Business Rules: Extreme Monetary Ceilings
    # =========================================================================
    claimed_bounds = FEATURE_BOUNDS.get("CLM_claimed")
    if claimed_bounds and claimed_amount > claimed_bounds.hard_ceiling:
        multiplier = claimed_amount / claimed_bounds.train_max
        result.warnings.append(GuardrailWarning(
            code="EXTREME_CLAIMED_AMOUNT",
            severity="CRITICAL",
            feature="CLM_claimed",
            message=(
                f"Claimed amount ({claimed_amount:,.0f} FCFA) exceeds the absolute plausibility "
                f"ceiling of {claimed_bounds.hard_ceiling:,.0f} FCFA ({multiplier:,.0f}x training max). "
                f"Mandatory freeze and forensic audit required."
            ),
            original_value=claimed_amount,
        ))
        result.escalate_tier(
            "CRITICAL",
            "GUARDRAIL OVERRIDE: Claimed amount is astronomically beyond any plausible healthcare expenditure. Mandatory forensic audit required."
        )

    cpd_bounds = FEATURE_BOUNDS.get("CLM_cost_per_day")
    if cpd_bounds and cost_per_day > cpd_bounds.hard_ceiling:
        result.warnings.append(GuardrailWarning(
            code="EXTREME_COST_PER_DAY",
            severity="CRITICAL",
            feature="CLM_cost_per_day",
            message=(
                f"Daily cost ({cost_per_day:,.0f} FCFA/day) exceeds the plausibility ceiling "
                f"of {cpd_bounds.hard_ceiling:,.0f} FCFA/day."
            ),
            original_value=cost_per_day,
        ))
        result.escalate_tier(
            "CRITICAL",
            "GUARDRAIL OVERRIDE: Daily expenditure is beyond plausible healthcare limits. Mandatory freeze required."
        )

    # =========================================================================
    # 2. Financial Reconciliation & Line-Item Consistency Guardrails
    # =========================================================================
    svc_count = int(claim.service_lines_count) if (claim and claim.service_lines_count is not None) else int(feature_dict.get("SVC_n_lines", 1))
    svc_asked = float(claim.service_asked_total) if (claim and claim.service_asked_total is not None) else float(feature_dict.get("SVC_asked_total", claimed_amount))
    itm_count = int(claim.item_lines_count) if (claim and claim.item_lines_count is not None) else int(feature_dict.get("ITM_n_lines", 0))
    itm_asked = float(claim.item_asked_total) if (claim and claim.item_asked_total is not None) else float(feature_dict.get("ITM_asked_total", 0.0))

    total_itemized = svc_asked + itm_asked
    total_lines = svc_count + itm_count

    # 2.1 Blank Services Claim
    if claimed_amount > 0 and total_lines == 0:
        result.warnings.append(GuardrailWarning(
            code="BLANK_SERVICES_CLAIM",
            severity="CRITICAL",
            feature="SVC_n_lines",
            message=(
                f"Phantom claim: Claimed amount is {claimed_amount:,.0f} FCFA but zero service "
                f"lines and zero consumable items are itemized."
            ),
            original_value=0.0,
        ))
        result.escalate_tier(
            "CRITICAL",
            f"GUARDRAIL OVERRIDE: Claim bills {claimed_amount:,.0f} FCFA with zero itemized services/items. Immediate rejection required."
        )
    elif claimed_amount > 0 and total_itemized == 0 and total_lines > 0:
        result.warnings.append(GuardrailWarning(
            code="BLANK_SERVICES_CLAIM",
            severity="CRITICAL",
            feature="SVC_asked_total",
            message=(
                f"Phantom billing: Claim requests {claimed_amount:,.0f} FCFA across {total_lines} lines "
                f"but the sum of itemized service/item prices is 0.00 FCFA."
            ),
            original_value=0.0,
        ))
        result.escalate_tier(
            "CRITICAL",
            f"GUARDRAIL OVERRIDE: Itemized lines sum to 0 FCFA for a {claimed_amount:,.0f} FCFA claim."
        )

    # 2.2 Unitemized Claim Padding (Header vs. Itemized Gap)
    if claimed_amount > total_itemized:
        gap = claimed_amount - total_itemized
        unitemized_ratio = gap / claimed_amount if claimed_amount > 0 else 0.0

        if gap >= 10_000.0 and unitemized_ratio >= 0.80:
            result.warnings.append(GuardrailWarning(
                code="UNITEMIZED_CLAIM_PADDING",
                severity="CRITICAL",
                feature="CLM_header_line_gap",
                message=(
                    f"Severe reconciliation failure: {unitemized_ratio * 100:.1f}% of claimed amount "
                    f"({gap:,.0f} FCFA out of {claimed_amount:,.0f} FCFA) has no itemized service or item lines. "
                    f"Only {total_itemized:,.0f} FCFA is itemized."
                ),
                original_value=gap,
            ))
            result.escalate_tier(
                "CRITICAL",
                (
                    f"GUARDRAIL OVERRIDE: {unitemized_ratio * 100:.1f}% unitemized claim padding ({gap:,.0f} FCFA). "
                    f"Payment frozen pending itemized accounting audit."
                ),
            )
        elif gap >= 5_000.0 and unitemized_ratio >= 0.40:
            result.warnings.append(GuardrailWarning(
                code="UNITEMIZED_CLAIM_PADDING",
                severity="HIGH",
                feature="CLM_header_line_gap",
                message=(
                    f"Reconciliation discrepancy: {unitemized_ratio * 100:.1f}% of claimed amount "
                    f"({gap:,.0f} FCFA out of {claimed_amount:,.0f} FCFA) is unitemized."
                ),
                original_value=gap,
            ))
            result.escalate_tier(
                "HIGH_RISK",
                (
                    f"GUARDRAIL OVERRIDE: Header exceeds itemized lines by {gap:,.0f} FCFA "
                    f"({unitemized_ratio * 100:.1f}% unitemized). Route for manual accounting audit."
                ),
            )
        elif gap >= 2_000.0:
            result.warnings.append(GuardrailWarning(
                code="UNITEMIZED_CLAIM_PADDING",
                severity="MEDIUM",
                feature="CLM_header_line_gap",
                message=(
                    f"Header exceeds itemized lines by {gap:,.0f} FCFA "
                    f"({unitemized_ratio * 100:.1f}% unitemized)."
                ),
                original_value=gap,
            ))

    # 2.3 Inverted Line Items (Itemized sum significantly exceeds header)
    elif total_itemized > (claimed_amount + 2_000.0):
        excess = total_itemized - claimed_amount
        result.warnings.append(GuardrailWarning(
            code="INVERTED_LINE_ITEMS",
            severity="MEDIUM",
            feature="CLM_header_line_gap",
            message=(
                f"Itemized lines sum to {total_itemized:,.0f} FCFA, which exceeds the claimed header "
                f"({claimed_amount:,.0f} FCFA) by {excess:,.0f} FCFA. Verify copayment or arithmetic entry."
            ),
            original_value=-excess,
        ))

    # =========================================================================
    # 3. Statutory Tariff Compliance Guardrails
    # =========================================================================
    svc_breaches = int(claim.service_tariff_breaches) if (claim and claim.service_tariff_breaches is not None) else int(feature_dict.get("SVC_tariff_breaches", 0))
    tariff_ratio_max = float(claim.service_tariff_ratio_max) if (claim and claim.service_tariff_ratio_max is not None) else float(feature_dict.get("SVC_tariff_ratio_max", 1.0))
    tariff_ratio_mean = float(claim.service_tariff_ratio_mean) if (claim and claim.service_tariff_ratio_mean is not None) else float(feature_dict.get("SVC_tariff_ratio_mean", 1.0))
    svc_tariff_total = float(claim.service_tariff_total) if (claim and claim.service_tariff_total is not None) else float(feature_dict.get("SVC_tariff_total", claimed_amount))

    if tariff_ratio_max >= 4.0 or (tariff_ratio_mean >= 3.0 and svc_breaches >= 2):
        result.warnings.append(GuardrailWarning(
            code="STATUTORY_TARIFF_GOUGING",
            severity="CRITICAL",
            feature="SVC_tariff_ratio_max",
            message=(
                f"Severe statutory tariff breach: Maximum itemized service markup is {tariff_ratio_max:.2f}x "
                f"the official ceiling (mean markup: {tariff_ratio_mean:.2f}x, {svc_breaches} breaches)."
            ),
            original_value=tariff_ratio_max,
        ))
        result.escalate_tier(
            "CRITICAL",
            f"GUARDRAIL OVERRIDE: Statutory tariff gouging detected (up to {tariff_ratio_max:.1f}x official ceiling). Mandatory tariff inspection required."
        )
    elif tariff_ratio_max >= 2.0 or svc_breaches >= 1:
        result.warnings.append(GuardrailWarning(
            code="TARIFF_BREACH_DETECTED",
            severity="HIGH",
            feature="SVC_tariff_breaches",
            message=(
                f"{svc_breaches} service line(s) exceed official statutory tariffs "
                f"(max markup: {tariff_ratio_max:.2f}x standard rate)."
            ),
            original_value=float(svc_breaches),
        ))
        result.escalate_tier(
            "HIGH_RISK",
            f"GUARDRAIL OVERRIDE: Statutory tariff breaches detected ({svc_breaches} lines, {tariff_ratio_max:.2f}x max). Manual tariff adjustment required."
        )

    if svc_tariff_total > 0 and claimed_amount >= 10_000.0:
        clm_tariff_ratio = claimed_amount / svc_tariff_total
        if clm_tariff_ratio >= 5.0:
            result.warnings.append(GuardrailWarning(
                code="CLAIM_VS_TARIFF_ANOMALY",
                severity="HIGH",
                feature="CLM_vs_tariff_total",
                message=(
                    f"Total claim amount ({claimed_amount:,.0f} FCFA) is {clm_tariff_ratio:.1f}x the total "
                    f"statutory tariff allowable for these services ({svc_tariff_total:,.0f} FCFA)."
                ),
                original_value=clm_tariff_ratio,
            ))
            result.escalate_tier(
                "HIGH_RISK",
                f"GUARDRAIL OVERRIDE: Claim is {clm_tariff_ratio:.1f}x official tariff total. Tariff audit required."
            )

    # =========================================================================
    # 4. Insurance Policy Validity & Temporal Eligibility Rules
    # =========================================================================
    date_from = claim.date_from if claim else None
    policy_exp = claim.policy_expiry_date if claim else None
    policy_start = claim.policy_start_date if claim else None
    policy_enroll = claim.policy_enrollment_date if claim else None

    # 4.1 Expired Policy
    if policy_exp is not None and date_from is not None and date_from > policy_exp:
        days_exp = (date_from - policy_exp).days
        result.warnings.append(GuardrailWarning(
            code="POLICY_EXPIRED_TREATMENT",
            severity="CRITICAL",
            feature="POL_days_to_expiry",
            message=(
                f"Treatment date ({date_from}) is {days_exp} day(s) after insurance policy expiration ({policy_exp}). "
                f"Service rendered outside coverage window."
            ),
            original_value=float(-days_exp),
        ))
        result.escalate_tier(
            "CRITICAL",
            f"GUARDRAIL OVERRIDE: Care delivered post-policy expiration ({days_exp} days expired). Claim ineligible for reimbursement."
        )

    # 4.2 Pre-Coverage Treatment
    if policy_start is not None and date_from is not None and date_from < policy_start:
        days_before = (policy_start - date_from).days
        result.warnings.append(GuardrailWarning(
            code="PRE_COVERAGE_TREATMENT",
            severity="CRITICAL",
            feature="POL_days_since_start",
            message=(
                f"Treatment date ({date_from}) is {days_before} day(s) before policy activation ({policy_start}). "
                f"Insuree was not active at time of service."
            ),
            original_value=float(-days_before),
        ))
        result.escalate_tier(
            "CRITICAL",
            f"GUARDRAIL OVERRIDE: Treatment predates policy activation ({days_before} days prior). Claim ineligible for reimbursement."
        )

    # 4.3 Pre-Enrollment Treatment
    if policy_enroll is not None and date_from is not None and date_from < policy_enroll:
        days_before_enroll = (policy_enroll - date_from).days
        result.warnings.append(GuardrailWarning(
            code="PRE_ENROLLMENT_TREATMENT",
            severity="CRITICAL",
            feature="POL_days_since_enroll",
            message=(
                f"Treatment date ({date_from}) is {days_before_enroll} day(s) before insuree enrollment date ({policy_enroll})."
            ),
            original_value=float(-days_before_enroll),
        ))
        result.escalate_tier(
            "CRITICAL",
            f"GUARDRAIL OVERRIDE: Treatment predates insuree enrollment ({days_before_enroll} days prior). Claim ineligible for reimbursement."
        )

    # 4.4 Missing Insurance Policy
    flag_no_policy = feature_dict.get("FLAG_no_policy_found", 0)
    if flag_no_policy == 1 and claimed_amount >= 5_000.0:
        result.warnings.append(GuardrailWarning(
            code="MISSING_INSURANCE_POLICY",
            severity="HIGH",
            feature="FLAG_no_policy_found",
            message=f"No active insurance policy found in openIMIS registry for claim of {claimed_amount:,.0f} FCFA.",
            original_value=1.0,
        ))
        result.escalate_tier(
            "HIGH_RISK",
            "GUARDRAIL OVERRIDE: No insurance policy record attached to claim. Manual beneficiary verification required."
        )

    # =========================================================================
    # 5. Clinical & Temporal Plausibility Guardrails
    # =========================================================================
    date_to = claim.date_to if claim else None
    date_claimed = claim.date_claimed if claim else None
    care_type = claim.care_type if claim else str(feature_dict.get("CareType", "OPD"))
    hf_level = claim.hf_level if claim else str(feature_dict.get("HF_level", "H"))

    # 5.1 Negative Length of Stay
    if los < 0 or (date_from is not None and date_to is not None and date_to < date_from):
        result.warnings.append(GuardrailWarning(
            code="NEGATIVE_LENGTH_OF_STAY",
            severity="CRITICAL",
            feature="CLM_los",
            message=f"Chronological anomaly: Service end date ({date_to}) precedes start date ({date_from}). Length of stay is {los} days.",
            original_value=float(los),
        ))
        result.escalate_tier(
            "CRITICAL",
            "GUARDRAIL OVERRIDE: Chronological impossibility (negative length of stay). Invalid claim submission."
        )

    # 5.2 Pre-Discharge Claim Submission
    if date_claimed is not None and date_to is not None and date_claimed < date_to:
        days_premature = (date_to - date_claimed).days
        result.warnings.append(GuardrailWarning(
            code="PRE_DISCHARGE_SUBMISSION",
            severity="HIGH",
            feature="CLM_delay",
            message=(
                f"Premature submission: Claim submitted on {date_claimed}, but discharge date is recorded as {date_to} "
                f"({days_premature} day(s) in the future)."
            ),
            original_value=float(-days_premature),
        ))
        result.escalate_tier(
            "HIGH_RISK",
            f"GUARDRAIL OVERRIDE: Claim submitted {days_premature} day(s) prior to discharge date. Premature billing."
        )

    # 5.3 Outpatient Extended LOS
    if care_type == "OPD" and los > 2:
        result.warnings.append(GuardrailWarning(
            code="OPD_EXTENDED_LOS",
            severity="HIGH",
            feature="CLM_los",
            message=(
                f"Care type is OPD (Outpatient) but length of stay is {los} days. "
                f"Outpatient visits must be same-day or 24-hour observation. Extended stays must be categorized as Inpatient (IPD)."
            ),
            original_value=float(los),
        ))
        result.escalate_tier(
            "HIGH_RISK",
            f"GUARDRAIL OVERRIDE: Outpatient (OPD) claim with {los}-day hospitalization. Verify admission category."
        )

    # 5.4 Extreme Inpatient LOS (> 365 days)
    if los > 365:
        result.warnings.append(GuardrailWarning(
            code="EXTREME_INPATIENT_LOS",
            severity="CRITICAL",
            feature="CLM_los",
            message=f"Hospitalization length of stay ({los} days) exceeds 365 days. Clinically implausible without formal audit justification.",
            original_value=float(los),
        ))
        result.escalate_tier(
            "CRITICAL",
            f"GUARDRAIL OVERRIDE: Hospital stay exceeds 1 year ({los} days). Mandatory clinical audit required."
        )

    # =========================================================================
    # 6. Facility Scope of Practice Guardrails
    # =========================================================================
    if hf_level in ("D", "C") and care_type == "IPD" and los > 5:
        result.warnings.append(GuardrailWarning(
            code="FACILITY_LEVEL_SCOPE_MISMATCH",
            severity="HIGH",
            feature="HF_level",
            message=(
                f"Facility level '{hf_level}' (Dispensary/Health Center) billed an inpatient stay of {los} days. "
                f"Primary care facilities are not accredited for multi-day inpatient hospitalizations."
            ),
            original_value=float(los),
        ))
        result.escalate_tier(
            "HIGH_RISK",
            f"GUARDRAIL OVERRIDE: Facility level '{hf_level}' billed extended inpatient stay ({los} days). Scope of practice violation."
        )

    # =========================================================================
    # 7. Out-of-Distribution (OOD) Detection on Bounded Features
    # =========================================================================
    for feat_name, bounds in FEATURE_BOUNDS.items():
        val = feature_dict.get(feat_name)
        if val is None:
            continue
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue

        if abs(val_f) > bounds.train_max:
            result.is_ood = True
            severity = "HIGH" if abs(val_f) > bounds.hard_ceiling else "MEDIUM"
            # Don't duplicate already-reported CRITICAL warnings
            already_reported = any(
                w.feature == feat_name and w.severity == "CRITICAL"
                for w in result.warnings
            )
            if not already_reported:
                result.warnings.append(GuardrailWarning(
                    code="OOD_FEATURE",
                    severity=severity,
                    feature=feat_name,
                    message=(
                        f"{bounds.name} ({val_f:,.2f} {bounds.unit}) exceeds the training maximum "
                        f"of {bounds.train_max:,.2f} {bounds.unit}. The model has never seen this value "
                        f"range and its prediction may be unreliable for this feature."
                    ),
                    original_value=val_f,
                ))
        elif abs(val_f) > bounds.p999:
            result.warnings.append(GuardrailWarning(
                code="EXTREME_PERCENTILE",
                severity="INFO",
                feature=feat_name,
                message=(
                    f"{bounds.name} ({val_f:,.2f} {bounds.unit}) is above the 99.9th percentile "
                    f"({bounds.p999:,.2f} {bounds.unit}) of training data. Value is unusual but "
                    f"within the training range."
                ),
                original_value=val_f,
            ))

    return result


def cap_features(
    feature_dict: Dict[str, Any],
    guardrail_result: GuardrailResult,
) -> Dict[str, Any]:
    """
    Winsorizes (caps) extreme numeric feature values at training-observed bounds.

    This ensures the LightGBM model operates within its training distribution,
    preventing the tree-split saturation problem where extreme values get the
    same score as the training maximum.

    The original values are preserved in the guardrail warnings for audit purposes.
    """
    capped = dict(feature_dict)

    for feat_name, bounds in FEATURE_BOUNDS.items():
        if feat_name not in capped:
            continue
        try:
            val = float(capped[feat_name])
        except (ValueError, TypeError):
            continue

        # Cap at training max — the most the model could have possibly learned from
        if val > bounds.train_max:
            guardrail_result.warnings.append(GuardrailWarning(
                code="FEATURE_CAPPED",
                severity="INFO",
                feature=feat_name,
                message=(
                    f"{bounds.name} capped from {val:,.2f} to {bounds.train_max:,.2f} {bounds.unit} "
                    f"for model scoring (original value preserved in warnings)."
                ),
                original_value=val,
                capped_value=bounds.train_max,
            ))
            capped[feat_name] = bounds.train_max
            guardrail_result.was_capped = True
        elif val < -bounds.train_max:
            capped[feat_name] = -bounds.train_max
            guardrail_result.was_capped = True

    return capped


def format_guardrail_warnings(result: GuardrailResult) -> List[Dict[str, Any]]:
    """Converts GuardrailResult warnings to JSON-serializable format for API response."""
    return [
        {
            "code": w.code,
            "severity": w.severity,
            "feature": w.feature,
            "message": w.message,
            "original_value": w.original_value,
            "capped_value": w.capped_value,
        }
        for w in result.warnings
        # Exclude INFO-level cap messages from API response to reduce noise
        if w.code != "FEATURE_CAPPED"
    ]
