"use client";

import React from "react";
import { ShapExplanation } from "../types";

interface ShapExplainerProps {
  explanations: ShapExplanation;
}

export default function ShapExplainer({ explanations }: ShapExplainerProps) {
  const { top_risk_drivers, top_mitigating_factors } = explanations;

  return (
    <div className="shap-section">
      {/* Risk Drivers */}
      <div className="shap-title" style={{ color: "#f87171" }}>
        <span>Top Contributing Risk Drivers (Why it was flagged)</span>
      </div>

      {top_risk_drivers.length > 0 ? (
        <div className="shap-list">
          {top_risk_drivers.map((item, idx) => (
            <div key={idx} className="shap-card risk">
              <div className="shap-info">
                <span className="shap-name">{item.display_name}</span>
                <span className="shap-rationale">{item.explanation}</span>
              </div>
              <div className="shap-stats">
                <span className="shap-impact positive">
                  +{item.shap_importance.toFixed(2)} SHAP
                </span>
                <span className="shap-val">Value: {item.value}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          No significant positive risk drivers identified.
        </p>
      )}

      {/* Mitigating Factors */}
      <div className="shap-title" style={{ color: "#34d399" }}>
        <span>Top Mitigating Factors (Evidence supporting claim validity)</span>
      </div>

      {top_mitigating_factors.length > 0 ? (
        <div className="shap-list">
          {top_mitigating_factors.map((item, idx) => (
            <div key={idx} className="shap-card mitigating">
              <div className="shap-info">
                <span className="shap-name">{item.display_name}</span>
                <span className="shap-rationale">{item.explanation}</span>
              </div>
              <div className="shap-stats">
                <span className="shap-impact negative">
                  {item.shap_importance.toFixed(2)} SHAP
                </span>
                <span className="shap-val">Value: {item.value}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          No substantial mitigating factors were found for this claim.
        </p>
      )}
    </div>
  );
}
