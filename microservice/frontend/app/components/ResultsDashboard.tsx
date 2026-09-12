"use client";

import React, { useState } from "react";
import { ClaimPredictionResponse } from "../types";
import ShapExplainer from "./ShapExplainer";

interface ResultsDashboardProps {
  result: ClaimPredictionResponse | null;
  isLoading: boolean;
  error: string | null;
}

const TIER_LABELS: Record<string, string> = {
  CRITICAL: "Critical",
  HIGH_RISK: "High risk",
  MODERATE_RISK: "Moderate risk",
  LOW_RISK: "Low risk",
};

function Shell({
  subtitle,
  action,
  children,
}: {
  subtitle: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-title">Audit triage result</div>
          <div className="panel-note">{subtitle}</div>
        </div>
        {action}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export default function ResultsDashboard({
  result,
  isLoading,
  error,
}: ResultsDashboardProps) {
  const [copied, setCopied] = useState<boolean>(false);

  if (isLoading) {
    return (
      <Shell subtitle="Scoring in progress">
        <div className="skeleton" style={{ height: "48px", width: "45%" }} />
        <div className="skeleton" style={{ height: "6px" }} />
        <div className="skeleton" style={{ height: "62px" }} />
        <div className="skeleton" style={{ height: "44px" }} />
        <div className="skeleton" style={{ height: "78px" }} />
        <div className="skeleton" style={{ height: "78px" }} />
      </Shell>
    );
  }

  if (error) {
    return (
      <Shell subtitle="Could not reach the scoring service">
        <div className="notice alert">
          <strong>Service unavailable</strong>
          {error}
        </div>
        <div className="notice">
          <strong>Start the microservice</strong>
          <code>uvicorn service.app:app --host 0.0.0.0 --port 8000</code>
        </div>
      </Shell>
    );
  }

  if (!result) {
    return (
      <Shell subtitle="No claim scored yet">
        <div className="placeholder">
          <h3>Nothing to review yet</h3>
          <p>
            Complete the claim details, paste a JSON payload, or load one of the
            sample claims to see the risk score and the factors behind it.
          </p>
        </div>
      </Shell>
    );
  }

  const { prediction, explanations, claim_id, latency_ms } = result;
  const tierClass = prediction.risk_tier.toLowerCase();
  const tierLabel =
    TIER_LABELS[prediction.risk_tier] ??
    prediction.risk_tier.replace(/_/g, " ").toLowerCase();

  const risk = Math.max(0, Math.min(100, prediction.fraud_risk_percentage));
  const threshold = Math.max(
    0,
    Math.min(100, prediction.decision_threshold * 100)
  );

  const copySummary = () => {
    const summary = `openIMIS Claim AI Verification Summary
Claim ID: ${claim_id || "N/A"}
Risk Tier: ${prediction.risk_tier}
Fraud/Rejection Risk: ${prediction.fraud_risk_percentage}%
Action: ${prediction.action_recommendation}
Top Risk Drivers: ${explanations.top_risk_drivers
      .map((d) => `${d.display_name} (+${d.shap_importance})`)
      .join(", ")}
Latency: ${latency_ms} ms`;

    navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Shell
      subtitle={claim_id ? `Claim ${claim_id}` : "Unreferenced claim"}
      action={
        <button type="button" className="btn" onClick={copySummary}>
          {copied ? "Copied" : "Copy summary"}
        </button>
      }
    >
      {/* Headline score */}
      <div className="score-block">
        <div>
          <span className="score-value">{risk.toFixed(1)}%</span>
          <div className="score-caption">
            Calibrated probability of fraud or rejection
          </div>
        </div>
        <div className={`tier ${tierClass}`}>{tierLabel}</div>
      </div>

      {/* Risk against the alert cutoff */}
      <div className="scale">
        <div className="scale-track">
          <div
            className={`scale-fill ${tierClass}`}
            style={{ width: `${risk}%` }}
          />
          <div className="scale-marker" style={{ left: `${threshold}%` }} />
        </div>
        <div className="scale-legend">
          <span>0%</span>
          <span>
            Alert cutoff <b>{threshold.toFixed(1)}%</b> —{" "}
            {prediction.is_flagged ? "exceeded" : "not reached"}
          </span>
          <span>100%</span>
        </div>
      </div>

      {/* Recommended action */}
      <div className={`recommendation ${tierClass}`}>
        <span className="eyebrow">Recommended action</span>
        <p>{prediction.action_recommendation}</p>
      </div>

      {/* Supporting numbers */}
      <div className="meta-strip">
        <div>
          <span className="eyebrow">Raw score</span>
          <b>{(prediction.raw_model_score * 100).toFixed(1)}%</b>
        </div>
        <div>
          <span className="eyebrow">Flagged</span>
          <b>{prediction.is_flagged ? "Yes" : "No"}</b>
        </div>
        <div>
          <span className="eyebrow">Response time</span>
          <b>{latency_ms.toFixed(1)} ms</b>
        </div>
      </div>

      <ShapExplainer explanations={explanations} />
    </Shell>
  );
}
