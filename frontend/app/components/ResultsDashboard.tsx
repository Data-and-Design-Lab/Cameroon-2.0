"use client";

import React, { useState } from "react";
import { ClaimPredictionResponse } from "../types";
import ShapExplainer from "./ShapExplainer";

interface ResultsDashboardProps {
  result: ClaimPredictionResponse | null;
  isLoading: boolean;
  error: string | null;
}

export default function ResultsDashboard({
  result,
  isLoading,
  error,
}: ResultsDashboardProps) {
  const [copied, setCopied] = useState<boolean>(false);

  if (isLoading) {
    return (
      <div className="glass-panel" style={{ minHeight: "520px" }}>
        <div className="empty-state" style={{ minHeight: "440px" }}>
          <div className="spinner" style={{ width: "42px", height: "42px", marginBottom: "1.25rem" }} />
          <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-main)" }}>
            Running Fraud & Anomaly Inference...
          </h3>
          <p style={{ color: "var(--text-dim)", marginTop: "0.5rem", maxWidth: "360px" }}>
            Processing 51 relational features, point-in-time policy math, isotonic probability calibration, and exact TreeSHAP attributions.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel" style={{ minHeight: "520px" }}>
        <div
          style={{
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            borderRadius: "12px",
            padding: "1.5rem",
            color: "#fca5a5",
          }}
        >
          <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "0.5rem" }}>
            Microservice Communication Error
          </h3>
          <p style={{ fontSize: "0.9rem", color: "#fecaca" }}>{error}</p>
          <p style={{ fontSize: "0.8rem", color: "var(--text-dim)", marginTop: "1rem" }}>
            Make sure the FastAPI microservice is running:
            <br />
            <code style={{ color: "#38bdf8" }}>uvicorn service.app:app --host 0.0.0.0 --port 8000</code>
          </p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="glass-panel" style={{ minHeight: "520px" }}>
        <div className="empty-state" style={{ minHeight: "440px" }}>
          <div className="empty-icon" style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-dim)" }}>Results</div>
          <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-main)" }}>
            Awaiting Claim Submission
          </h3>
          <p style={{ color: "var(--text-dim)", marginTop: "0.5rem", maxWidth: "360px" }}>
            Fill out the form on the left, drag-and-drop an openIMIS claim JSON file, or click one of the quick presets above to view live predictions.
          </p>
        </div>
      </div>
    );
  }

  const { prediction, explanations, claim_id, latency_ms } = result;
  const tierClass = prediction.risk_tier.toLowerCase();

  const copySummary = () => {
    const summary = `openIMIS Claim AI Verification Summary
Claim ID: ${claim_id || "N/A"}
Risk Tier: ${prediction.risk_tier}
Fraud/Rejection Risk: ${prediction.fraud_risk_percentage}%
Action: ${prediction.action_recommendation}
Top Risk Drivers: ${explanations.top_risk_drivers.map((d) => `${d.display_name} (+${d.shap_importance})`).join(", ")}
Latency: ${latency_ms} ms`;

    navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-panel">
      {/* Header */}
      <div className="results-header">
        <div>
          <span style={{ fontSize: "0.78rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 700 }}>
            Audit Triage Result
          </span>
          <h2 style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--text-main)" }}>
            {claim_id ? `Claim ${claim_id}` : "Claim Verification Report"}
          </h2>
        </div>

        <button
          type="button"
          className="preset-btn"
          onClick={copySummary}
          title="Copy adjudication summary to clipboard"
        >
          {copied ? "Copied!" : "Copy Triage Summary"}
        </button>
      </div>

      {/* Primary Risk Overview Card */}
      <div className={`risk-overview-card ${tierClass}`}>
        <div className="gauge-section">
          <div className="risk-percentage-display">
            <span className={`risk-number ${tierClass}`}>
              {prediction.fraud_risk_percentage.toFixed(1)}%
            </span>
            <span className="risk-label">Calibrated Fraud / Rejection Risk</span>
          </div>

          <div className={`risk-tier-pill ${tierClass}`}>
            {prediction.risk_tier.replace("_", " ")}
          </div>
        </div>

        {/* Action Recommendation Box */}
        <div className={`action-box ${tierClass}`}>
          <div style={{ fontSize: "0.75rem", textTransform: "uppercase", opacity: 0.8, marginBottom: "0.2rem" }}>
            Recommended Adjudication Action
          </div>
          <div>{prediction.action_recommendation}</div>
        </div>

        {/* Decision Threshold Meta */}
        <div className="decision-meta">
          <div>
            Raw Score: <strong>{(prediction.raw_model_score * 100).toFixed(1)}%</strong>
          </div>
          <div>
            Alert Cutoff: <strong>{(prediction.decision_threshold * 100).toFixed(1)}%</strong>
          </div>
          <div>
            Latency: <strong>{latency_ms.toFixed(1)} ms</strong>
          </div>
        </div>
      </div>

      {/* TreeSHAP Explanation Section */}
      <ShapExplainer explanations={explanations} />
    </div>
  );
}
