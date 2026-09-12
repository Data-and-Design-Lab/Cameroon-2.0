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

const SAMPLES: { label: string; claim: ClaimInput }[] = [
  { label: "Routine outpatient", claim: legitimateClaim as unknown as ClaimInput },
  { label: "Expired policy + markup", claim: fraudulentClaim as unknown as ClaimInput },
  { label: "High-cost inpatient", claim: borderlineClaim as unknown as ClaimInput },
];

export default function Presets({ onSelectPreset, onAutoSubmit }: PresetsProps) {
  const handleLoadAndScore = (claim: ClaimInput) => {
    onSelectPreset(claim);
    if (onAutoSubmit) {
      onAutoSubmit(claim);
    }
  };

  return (
    <div className="samples">
      <span className="eyebrow">Sample claims</span>
      {SAMPLES.map((sample) => (
        <button
          key={sample.label}
          type="button"
          className="btn"
          onClick={() => handleLoadAndScore(sample.claim)}
        >
          {sample.label}
        </button>
      ))}
    </div>
  );
}
