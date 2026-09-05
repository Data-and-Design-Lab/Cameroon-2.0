"""
openIMIS Python Client Integration Example.

Demonstrates how openIMIS or an external claims processing software can call
the Fraud & Rejection Detection Microservice to verify claims before payment.
"""

import json
import sys
from datetime import date
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from service.app import app
from fastapi.testclient import TestClient

# In a production environment with a deployed microservice, you would use:
# import requests
# API_BASE_URL = "http://localhost:8000"
# response = requests.post(f"{API_BASE_URL}/api/v1/predict/claim", json=payload)

def run_demonstration():
    client = TestClient(app)
    
    print("=" * 75)
    print(" Cameroon openIMIS Claim Fraud & Rejection Prediction Service Demo")
    print("=" * 75)
    
    # 1. Check Service Health & Model Stats
    health = client.get("/health").json()
    print(f"\n[1] Microservice Status: {health['status'].upper()}")
    print(f"    Model Family       : {health['model_family']}")
    print(f"    Validation ROC-AUC : {health['roc_auc_test']}")
    print(f"    Validation PR-AUC  : {health['pr_auc_test']}")
    print(f"    Alert Threshold    : {health['decision_threshold']}")
    
    # 2. Legitimate Standard Claim
    legit_claim = {
        "claim_id": "CLM-YAOUNDE-2026-0182",
        "claimed_amount": 14500.0,
        "date_from": "2026-03-01",
        "date_to": "2026-03-02",
        "date_claimed": "2026-03-03",
        "care_type": "OPD",
        "visit_type": "O",
        "hfid": 404,
        "hf_level": "H",
        "hf_legalform": "G",
        "geo_region": "Centre",
        "geo_district": "Guider",
        "icdid": 1931,
        "dx_chapter": "J",
        "policy_start_date": "2025-01-01",
        "policy_expiry_date": "2026-12-31",
        "service_lines_count": 3,
        "service_asked_total": 14500.0,
        "service_tariff_total": 14500.0,
        "service_tariff_breaches": 0,
    }
    
    print("\n[2] Evaluating Standard Legitimate Claim (CLM-YAOUNDE-2026-0182)...")
    res_legit = client.post("/api/v1/predict/claim", json=legit_claim).json()
    pred = res_legit["prediction"]
    print(f"    Risk Tier          : {pred['risk_tier']}")
    print(f"    Fraud/Rejection %  : {pred['fraud_risk_percentage']}%")
    print(f"    Alert Triggered    : {pred['is_flagged']}")
    print(f"    Action             : {pred['action_recommendation']}")
    print(f"    Latency            : {res_legit['latency_ms']} ms")
    
    # 3. Suspicious / Fraudulent Claim (Expired Policy + 10x Tariff Markup)
    fraud_claim = {
        "claim_id": "CLM-SUSPICIOUS-2026-9901",
        "claimed_amount": 165000.0,
        "date_from": "2026-04-10",
        "date_to": "2026-04-10",
        "date_claimed": "2026-05-20",  # 40-day delay
        "care_type": "OPD",
        "visit_type": "E",
        "hfid": 404,
        "geo_region": "Centre",
        "policy_start_date": "2024-01-01",
        "policy_expiry_date": "2024-12-31",  # Expired over a year ago!
        "service_lines_count": 1,
        "service_asked_total": 165000.0,
        "service_tariff_total": 12000.0,     # Massive mark-up over tariff
        "service_tariff_breaches": 1,
    }
    
    print("\n[3] Evaluating High-Risk Claim (CLM-SUSPICIOUS-2026-9901)...")
    res_fraud = client.post("/api/v1/predict/claim", json=fraud_claim).json()
    pred_f = res_fraud["prediction"]
    expl_f = res_fraud["explanations"]
    print(f"    Risk Tier          : {pred_f['risk_tier']}")
    print(f"    Fraud/Rejection %  : {pred_f['fraud_risk_percentage']}%")
    print(f"    Alert Triggered    : {pred_f['is_flagged']}")
    print(f"    Action             : {pred_f['action_recommendation']}")
    print(f"    Latency            : {res_fraud['latency_ms']} ms")
    print("\n    Top TreeSHAP Risk Drivers:")
    for i, driver in enumerate(expl_f["top_risk_drivers"], 1):
        print(f"      {i}. {driver['display_name']} (Value: {driver['value']})")
        print(f"         Impact: +{driver['shap_importance']} | Rationale: {driver['explanation']}")
        
    print("\n" + "=" * 75)
    print(" Demonstration Completed Successfully!")
    print("=" * 75)

if __name__ == "__main__":
    run_demonstration()
