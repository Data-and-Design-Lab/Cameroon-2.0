"use client";

import React from "react";
import { ShapExplanation, TopFeatureContribution } from "../types";

interface ShapExplainerProps {
  explanations: ShapExplanation;
}

function FactorList({
  items,
  direction,
  scale,
  emptyNote,
}: {
  items: TopFeatureContribution[];
  direction: "up" | "down";
  scale: number;
  emptyNote: string;
}) {
  if (items.length === 0) {
    return <p className="empty-note">{emptyNote}</p>;
  }

  return (
    <div>
      {items.map((item, idx) => {
        const magnitude = Math.abs(item.shap_importance);
        const width = scale > 0 ? Math.max(3, (magnitude / scale) * 100) : 0;

        return (
          <div className="factor" key={`${item.feature}-${idx}`}>
            <span className="factor-name">{item.display_name}</span>
            <span className="factor-bar-track">
              <span
                className={`factor-bar-fill ${direction}`}
                style={{ width: `${width}%` }}
              />
            </span>
            <span className="factor-weight">
              {direction === "up" ? "+" : "−"}
              {magnitude.toFixed(2)}
            </span>
            <p className="factor-why">{item.explanation}</p>
            <span className="factor-value">{item.value}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function ShapExplainer({ explanations }: ShapExplainerProps) {
  const { top_risk_drivers, top_mitigating_factors } = explanations;

  // Share one bar scale across both lists so magnitudes stay comparable.
  const scale = Math.max(
    ...[...top_risk_drivers, ...top_mitigating_factors].map((item) =>
      Math.abs(item.shap_importance)
    ),
    0
  );

  return (
    <div className="explain">
      <div className="explain-group">
        <div className="explain-head">
          <h4>What raised the score</h4>
          <span className="eyebrow">SHAP weight</span>
        </div>
        <FactorList
          items={top_risk_drivers}
          direction="up"
          scale={scale}
          emptyNote="No factor pushed this claim towards rejection."
        />
      </div>

      <div className="explain-group">
        <div className="explain-head">
          <h4>What lowered the score</h4>
          <span className="eyebrow">SHAP weight</span>
        </div>
        <FactorList
          items={top_mitigating_factors}
          direction="down"
          scale={scale}
          emptyNote="No mitigating evidence was found for this claim."
        />
      </div>
    </div>
  );
}
