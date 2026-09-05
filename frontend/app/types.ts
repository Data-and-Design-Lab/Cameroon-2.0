export interface ClaimInput {
  claim_id?: string;
  claimed_amount: number;
  date_from: string;
  date_to: string;
  date_claimed?: string;
  care_type: string;
  visit_type: string;
  has_explanation?: boolean;
  hfid: number;
  hf_level: string;
  hf_caretype: string;
  hf_legalform: string;
  geo_region: string;
  geo_district: string;
  icdid: number;
  dx_chapter?: string;
  policy_start_date?: string;
  policy_expiry_date?: string;
  policy_enrollment_date?: string;
  service_lines_count: number;
  service_asked_total?: number;
  service_tariff_total?: number;
  service_asked_mean?: number;
  service_asked_max?: number;
  service_tariff_breaches: number;
  service_tariff_ratio_max?: number;
  service_tariff_ratio_mean?: number;
  service_n_distinct?: number;
  service_repeat_rate: number;
  service_top_line_share?: number;
  item_lines_count: number;
  item_asked_total: number;
}

export interface TopFeatureContribution {
  feature: string;
  display_name: string;
  value: string | number;
  impact_direction: "INCREASES_RISK" | "DECREASES_RISK";
  shap_importance: number;
  explanation: string;
}

export interface ShapExplanation {
  baseline_log_odds: number;
  top_risk_drivers: TopFeatureContribution[];
  top_mitigating_factors: TopFeatureContribution[];
}

export interface PredictionResult {
  is_flagged: boolean;
  risk_tier: "CRITICAL" | "HIGH_RISK" | "MODERATE_RISK" | "LOW_RISK";
  fraud_risk_percentage: number;
  raw_model_score: number;
  decision_threshold: number;
  action_recommendation: string;
}

export interface ClaimPredictionResponse {
  claim_id?: string;
  prediction: PredictionResult;
  explanations: ShapExplanation;
  latency_ms: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  model_loaded: boolean;
  model_family: string;
  roc_auc_test: number;
  pr_auc_test: number;
  decision_threshold: number;
  num_features: number;
}
