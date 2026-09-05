import sys
import time
import unittest
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from service.app import app


class TestFraudMicroservice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        """Test landing endpoint."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "operational")
        self.assertIn("model_performance", data)
        self.assertEqual(data["model_performance"]["roc_auc_test"], 0.8778)

    def test_health_endpoint(self):
        """Test healthcheck and model status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_loaded"])
        self.assertEqual(data["num_features"], 51)
        self.assertAlmostEqual(data["roc_auc_test"], 0.8778, places=3)
        self.assertAlmostEqual(data["pr_auc_test"], 0.7604, places=3)

    def test_schema_endpoint(self):
        """Test schema discovery endpoint."""
        response = self.client.get("/api/v1/schema")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["num_features"], 51)
        self.assertIn("CLM_claimed", data["features"])
        self.assertIn("POL_days_to_expiry", data["features"])
        self.assertIn("GEO_region", data["categorical_columns"])

    def test_predict_normal_claim(self):
        """Test scoring a standard compliant claim."""
        payload = {
            "claim_id": "CLM-NORMAL-001",
            "claimed_amount": 12000.0,
            "date_from": "2026-03-01",
            "date_to": "2026-03-02",
            "date_claimed": "2026-03-03",
            "care_type": "OPD",
            "visit_type": "O",
            "hfid": 404,
            "hf_level": "H",
            "hf_caretype": "B",
            "hf_legalform": "G",
            "geo_region": "Centre",
            "geo_district": "Guider",
            "icdid": 1931,
            "dx_chapter": "J",
            "policy_start_date": "2025-01-01",
            "policy_expiry_date": "2026-12-31",
            "policy_enrollment_date": "2024-12-01",
            "service_lines_count": 2,
            "service_asked_total": 12000.0,
            "service_tariff_total": 12000.0,
            "service_tariff_breaches": 0,
        }
        response = self.client.post("/api/v1/predict/claim", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["claim_id"], "CLM-NORMAL-001")
        pred = data["prediction"]
        self.assertIn("fraud_risk_percentage", pred)
        self.assertGreaterEqual(pred["fraud_risk_percentage"], 0.0)
        self.assertLessEqual(pred["fraud_risk_percentage"], 100.0)
        
        # Explanations check
        expl = data["explanations"]
        self.assertIn("top_risk_drivers", expl)
        self.assertIn("top_mitigating_factors", expl)
        self.assertLess(data["latency_ms"], 50.0)

    def test_predict_high_risk_claim(self):
        """Test scoring an anomalous claim with expired policy and extreme tariff markup."""
        payload = {
            "claim_id": "CLM-FRAUD-ALERT",
            "claimed_amount": 185000.0,
            "date_from": "2026-03-15",
            "date_to": "2026-03-15",
            "date_claimed": "2026-04-20",  # delayed
            "care_type": "OPD",
            "visit_type": "E",
            "hfid": 404,
            "policy_start_date": "2024-01-01",
            "policy_expiry_date": "2025-01-01",  # EXPIRED over 1 year ago!
            "service_lines_count": 1,
            "service_asked_total": 185000.0,
            "service_tariff_total": 15000.0,    # 12x tariff markup!
            "service_tariff_breaches": 1,
        }
        response = self.client.post("/api/v1/predict/claim", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        pred = data["prediction"]
        self.assertTrue(pred["is_flagged"])
        self.assertIn(pred["risk_tier"], ["HIGH_RISK", "CRITICAL"])
        self.assertGreater(pred["fraud_risk_percentage"], 50.0)
        
        # Verify SHAP caught the expired policy or tariff markup
        risk_drivers = [d["feature"] for d in data["explanations"]["top_risk_drivers"]]
        self.assertTrue(
            any(f in risk_drivers for f in ["POL_days_to_expiry", "CLM_vs_tariff_total", "FLAG_policy_expired", "CLM_cost_per_day"]),
            f"Expected risk driver not found in {risk_drivers}"
        )

    def test_edge_case_minimal_payload(self):
        """Test claim with only required fields and missing optional policy."""
        payload = {
            "claimed_amount": 5000.0,
            "date_from": "2026-02-01",
            "date_to": "2026-02-01",
        }
        response = self.client.post("/api/v1/predict/claim", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prediction", data)

    def test_edge_case_unknown_categorical(self):
        """Test unknown facility ID, unknown region, and unknown care type."""
        payload = {
            "claimed_amount": 7500.0,
            "date_from": "2026-02-01",
            "date_to": "2026-02-02",
            "care_type": "UNKNOWN_CARE_TYPE",
            "geo_region": "MARS_REGION",
            "geo_district": "NON_EXISTENT_DISTRICT",
            "hfid": 9999999,
            "icdid": 9999999,
        }
        response = self.client.post("/api/v1/predict/claim", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prediction", data)

    def test_predict_raw_features(self):
        """Test direct 51-feature scoring."""
        schema_resp = self.client.get("/api/v1/schema")
        features_list = schema_resp.json()["features"]
        
        feature_dict = {f: 0.0 for f in features_list}
        feature_dict["CareType"] = "OPD"
        feature_dict["VisitType"] = "O"
        feature_dict["HF_level"] = "H"
        feature_dict["HF_caretype"] = "B"
        feature_dict["HF_legalform"] = "G"
        feature_dict["GEO_region"] = "Centre"
        feature_dict["GEO_district"] = "Guider"
        feature_dict["DX_chapter"] = "J"
        feature_dict["Hfid"] = 404
        feature_dict["Icdid"] = 1931
        
        payload = {
            "claim_id": "CLM-RAW-TEST",
            "features": feature_dict,
        }
        response = self.client.post("/api/v1/predict/features", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["claim_id"], "CLM-RAW-TEST")
        self.assertIn("prediction", data)

    def test_batch_prediction(self):
        """Test scoring multiple claims in a single batch."""
        claims = [
            {
                "claim_id": f"BATCH-{i}",
                "claimed_amount": float(10000 + i * 5000),
                "date_from": "2026-01-01",
                "date_to": "2026-01-02",
            }
            for i in range(5)
        ]
        response = self.client.post("/api/v1/predict/batch", json={"claims": claims})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_claims"], 5)
        self.assertEqual(len(data["results"]), 5)
        self.assertIn("flagged_claims", data)


if __name__ == "__main__":
    unittest.main()
