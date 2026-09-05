"use client";

import React from "react";
import { ClaimInput } from "../types";

// Import sample claim data directly
import legitimateClaim from "../../sample_claims/legitimate_claim.json";
import fraudulentClaim from "../../sample_claims/fraudulent_claim.json";
import borderlineClaim from "../../sample_claims/borderline_claim.json";

interface PresetsProps {
  onSelectPreset: (claim: ClaimInput) => void;
  onAutoSubmit?: (claim: ClaimInput) => void;
}

export default function Presets({ onSelectPreset, onAutoSubmit }: PresetsProps) {
  const handleLoadAndScore = (claim: ClaimInput) => {
    onSelectPreset(claim);
    if (onAutoSubmit) {
      onAutoSubmit(claim);
    }
  };

  return (
    <div className="presets-card">
      <div className="presets-label">
        <span>Quick Demonstration Presets</span>
      </div>

      <div className="presets-buttons">
        <button
          type="button"
          className="preset-btn legit"
          onClick={() => handleLoadAndScore(legitimateClaim as unknown as ClaimInput)}
        >
          Load Standard Claim (Low Risk ~8%)
        </button>

        <button
          type="button"
          className="preset-btn fraud"
          onClick={() => handleLoadAndScore(fraudulentClaim as unknown as ClaimInput)}
        >
          Load Suspicious Claim (Expired Policy + Markup ~98%)
        </button>

        <button
          type="button"
          className="preset-btn borderline"
          onClick={() => handleLoadAndScore(borderlineClaim as unknown as ClaimInput)}
        >
          Load Inpatient Stay (High Cost ~65%)
        </button>
      </div>
    </div>
  );
}
