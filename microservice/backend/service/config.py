from pathlib import Path
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Model artifacts live in the repository-level `models/` directory
# (microservice/backend/service -> ... -> repository root). In the Docker image
# `models/` sits directly beside `service/`, so the search starts at the backend
# directory and walks up until a `models/` directory turns up.
_SEARCH_ROOTS = (BACKEND_DIR, *BACKEND_DIR.parents)
REPO_ROOT = next(
    (path for path in _SEARCH_ROOTS if (path / "models").is_dir()),
    BACKEND_DIR.parent.parent,
)
DEFAULT_MODEL_DIR = REPO_ROOT / "models" / "model_lightgbm_no_leakage"

class Settings(BaseSettings):
    app_title: str = "openIMIS Claim Fraud & Rejection Prediction Service"
    app_version: str = "1.0.0"
    app_description: str = (
        "Production-grade microservice for real-time healthcare claim fraud, "
        "anomaly detection, and rejection risk scoring with calibrated probabilities "
        "and exact TreeSHAP explanations."
    )
    
    # Model configuration
    model_dir: Path = DEFAULT_MODEL_DIR
    model_file: str = "lightgbm_model.txt"
    schema_file: str = "feature_schema.pkl"
    calibrator_file: str = "isotonic_calibrator.pkl"
    config_file: str = "lightgbm_config.json"
    
    # Adjudication alert decision threshold (optimal F-beta / capacity threshold from training)
    decision_threshold: float = 0.8751227354619026
    
    # Risk tier cutoffs (raw score)
    threshold_critical: float = 0.95
    threshold_high: float = 0.8751227354619026
    threshold_medium: float = 0.50

    class Config:
        env_prefix = "FRAUD_API_"

settings = Settings()
