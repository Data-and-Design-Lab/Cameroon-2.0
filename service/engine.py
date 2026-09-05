"""
Inference & Prediction Engine for openIMIS Fraud & Rejection Detection.
Manages in-memory LightGBM Booster, Isotonic Probability Calibrator, and SHAP generator.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from service.config import settings
from service.explainer import generate_explanations
from service.schemas import (
    ClaimInput,
    ClaimPredictionResponse,
    HealthResponse,
    PredictionResult,
    ShapExplanation,
)
from service.transformer import build_dataframe, claim_to_feature_dict

logger = logging.getLogger("fraud_service.engine")


class FraudModelEngine:
    """
    Singleton class managing the trained LightGBM model, schema, and calibrator.
    """
    _instance: Optional["FraudModelEngine"] = None

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or settings.model_dir
        self.is_loaded = False
        self.booster: Optional[lgb.Booster] = None
        self.calibrator = None
        self.schema: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}
        self.features: List[str] = []
        self.cat_features: List[str] = []
        self.categories: Dict[str, List[Any]] = {}
        self.decision_threshold: float = settings.decision_threshold
        self._load_artifacts()

    @classmethod
    def get_instance(cls) -> "FraudModelEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_artifacts(self) -> None:
        model_path = self.model_dir / settings.model_file
        schema_path = self.model_dir / settings.schema_file
        calibrator_path = self.model_dir / settings.calibrator_file
        config_path = self.model_dir / settings.config_file

        logger.info(f"Loading LightGBM model from {model_path}")
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at {model_path}")
        self.booster = lgb.Booster(model_file=str(model_path))

        logger.info(f"Loading feature schema from {schema_path}")
        self.schema = joblib.load(str(schema_path))
        self.features = self.schema["features"]
        self.cat_features = self.schema["categorical"]
        self.categories = self.schema["categories"]

        logger.info(f"Loading isotonic calibrator from {calibrator_path}")
        self.calibrator = joblib.load(str(calibrator_path))

        if config_path.exists():
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.decision_threshold = float(self.config.get("threshold", settings.decision_threshold))

        self.is_loaded = True
        logger.info(
            f"Model engine initialized successfully with {len(self.features)} features "
            f"and alert threshold {self.decision_threshold:.4f}"
        )

    def predict_df(
        self, df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Runs model prediction, isotonic probability calibration, and exact TreeSHAP computation.
        """
        if not self.is_loaded or self.booster is None:
            raise RuntimeError("Model is not initialized.")
            
        # 1. Raw decision tree prediction score (margin/probability)
        raw_scores = self.booster.predict(df)
        
        # 2. Calibrated empirical probability
        cal_probs = self.calibrator.transform(raw_scores)
        cal_probs = np.clip(cal_probs, 0.0, 1.0)
        
        # 3. Exact TreeSHAP attribution (N, 52) where last column is baseline
        contribs = self.booster.predict(df, pred_contrib=True)
        
        return raw_scores, cal_probs, contribs

    def _determine_tier_and_action(
        self, raw_score: float, cal_prob: float
    ) -> Tuple[str, str, bool]:
        """
        Determines risk tier, alert flag, and triage action.
        """
        is_flagged = bool(raw_score >= self.decision_threshold)
        
        if raw_score >= settings.threshold_critical:
            tier = "CRITICAL"
            action = "HIGH-PRIORITY AUDIT: Freeze payment; mandatory forensic review for potential fraud/invalidation."
        elif is_flagged:
            tier = "HIGH_RISK"
            action = "ALERT: Route claim to medical adjudication queue for manual eligibility/tariff inspection."
        elif raw_score >= settings.threshold_medium:
            tier = "MODERATE_RISK"
            action = "MEDIUM_RISK: Spot-check recommended; verify itemized tariff compliance if total exceeds threshold."
        else:
            tier = "LOW_RISK"
            action = "LOW_RISK: Fast-track automated adjudication approved; low rejection probability."

        return tier, action, is_flagged

    def score_claim(self, claim: ClaimInput) -> ClaimPredictionResponse:
        """
        Scores an individual openIMIS claim and generates detailed TreeSHAP explanations.
        """
        start_t = time.perf_counter()
        
        row_dict = claim_to_feature_dict(claim)
        df = build_dataframe([row_dict], self.features, self.cat_features, self.categories)
        
        raw_scores, cal_probs, contribs = self.predict_df(df)
        
        raw_score = float(raw_scores[0])
        cal_prob = float(cal_probs[0])
        shap_vector = contribs[0]
        
        feature_shap = shap_vector[:-1].tolist()
        baseline_log_odds = float(shap_vector[-1])
        
        top_pos, top_neg = generate_explanations(
            feature_names=self.features,
            shap_values=feature_shap,
            feature_values=row_dict,
            top_k=4,
        )
        
        tier, action, is_flagged = self._determine_tier_and_action(raw_score, cal_prob)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        
        return ClaimPredictionResponse(
            claim_id=claim.claim_id,
            prediction=PredictionResult(
                is_flagged=is_flagged,
                risk_tier=tier,
                fraud_risk_percentage=round(cal_prob * 100.0, 2),
                raw_model_score=round(raw_score, 4),
                decision_threshold=round(self.decision_threshold, 4),
                action_recommendation=action,
            ),
            explanations=ShapExplanation(
                baseline_log_odds=round(baseline_log_odds, 4),
                top_risk_drivers=top_pos,
                top_mitigating_factors=top_neg,
            ),
            latency_ms=round(elapsed_ms, 2),
        )

    def score_raw_features(
        self, feature_dict: Dict[str, Any], claim_id: Optional[str] = None
    ) -> ClaimPredictionResponse:
        """
        Scores a direct 51-feature dictionary.
        """
        start_t = time.perf_counter()
        
        df = build_dataframe([feature_dict], self.features, self.cat_features, self.categories)
        raw_scores, cal_probs, contribs = self.predict_df(df)
        
        raw_score = float(raw_scores[0])
        cal_prob = float(cal_probs[0])
        shap_vector = contribs[0]
        
        feature_shap = shap_vector[:-1].tolist()
        baseline_log_odds = float(shap_vector[-1])
        
        top_pos, top_neg = generate_explanations(
            feature_names=self.features,
            shap_values=feature_shap,
            feature_values=feature_dict,
            top_k=4,
        )
        
        tier, action, is_flagged = self._determine_tier_and_action(raw_score, cal_prob)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        
        return ClaimPredictionResponse(
            claim_id=claim_id,
            prediction=PredictionResult(
                is_flagged=is_flagged,
                risk_tier=tier,
                fraud_risk_percentage=round(cal_prob * 100.0, 2),
                raw_model_score=round(raw_score, 4),
                decision_threshold=round(self.decision_threshold, 4),
                action_recommendation=action,
            ),
            explanations=ShapExplanation(
                baseline_log_odds=round(baseline_log_odds, 4),
                top_risk_drivers=top_pos,
                top_mitigating_factors=top_neg,
            ),
            latency_ms=round(elapsed_ms, 2),
        )

    def score_batch(self, claims: List[ClaimInput]) -> List[ClaimPredictionResponse]:
        """
        Scores a batch of claims efficiently.
        """
        return [self.score_claim(c) for c in claims]

    def get_health_stats(self) -> HealthResponse:
        metrics = self.config.get("metrics_test", {})
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            model_loaded=self.is_loaded,
            model_family="LightGBM GBDT (Leakage-Free) + Isotonic Calibrator",
            roc_auc_test=round(float(metrics.get("roc_auc", 0.8778)), 4),
            pr_auc_test=round(float(metrics.get("pr_auc", 0.7604)), 4),
            decision_threshold=round(self.decision_threshold, 4),
            num_features=len(self.features),
        )
