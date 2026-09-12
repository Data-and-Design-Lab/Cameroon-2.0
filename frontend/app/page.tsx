"use client";

import React, { useState } from "react";
import Header from "./components/Header";
import Presets from "./components/Presets";
import ClaimForm from "./components/ClaimForm";
import JsonUploader from "./components/JsonUploader";
import ResultsDashboard from "./components/ResultsDashboard";
import { ClaimInput, ClaimPredictionResponse } from "./types";

import defaultClaim from "../sample_claims/legitimate_claim.json";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"form" | "json">("form");
  const [formData, setFormData] = useState<ClaimInput>(
    defaultClaim as unknown as ClaimInput
  );
  const [result, setResult] = useState<ClaimPredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const executePrediction = async (claimToScore: ClaimInput) => {
    setIsLoading(true);
    setError(null);

    // Direct URL first (most reliable on Windows), then proxy fallback
    const candidateUrls = [
      "http://127.0.0.1:8000/api/v1/predict/claim",
      "/api/proxy/api/v1/predict/claim",
    ];

    let lastError: any = null;
    let data: ClaimPredictionResponse | null = null;

    console.log("[Frontend] Submitting claim for AI verification:", claimToScore);

    for (const url of candidateUrls) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(claimToScore),
          signal: controller.signal,
        });
        clearTimeout(timeout);

        if (response.ok) {
          data = await response.json();
          console.log(`[Frontend] Successfully scored via ${url}:`, data);
          break;
        } else {
          const errData = await response.json().catch(() => ({}));
          lastError = new Error(errData.detail || `HTTP ${response.status}`);
          console.warn(`[Frontend] ${url} returned ${response.status}:`, errData);
        }
      } catch (err: any) {
        clearTimeout(timeout);
        console.warn(`[Frontend] ${url} failed:`, err.message);
        lastError = err;
      }
    }

    if (data) {
      setResult(data);
    } else {
      console.error("[Frontend] Connection failed on all candidates:", lastError);
      setError(
        lastError?.message ||
          "Could not connect to FastAPI backend on http://127.0.0.1:8000. Please verify backend is running."
      );
    }

    setIsLoading(false);
  };

  const handleSelectPreset = (presetClaim: ClaimInput) => {
    setFormData(presetClaim);
  };

  const handleAutoSubmit = (presetClaim: ClaimInput) => {
    setFormData(presetClaim);
    executePrediction(presetClaim);
  };

  return (
    <main className="app-container">
      <Header apiUrl="/api/proxy" />

      <div className="dashboard-grid">
        {/* Left: claim input */}
        <section className="panel">
          <div className="panel-head">
            <div>
              <div className="panel-title">Claim details</div>
              <div className="panel-note">
                {activeTab === "form"
                  ? "Enter the claim as submitted by the facility."
                  : "Send a raw openIMIS claim payload."}
              </div>
            </div>

            <div className="segmented" role="tablist" aria-label="Input method">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "form"}
                onClick={() => setActiveTab("form")}
              >
                Form
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "json"}
                onClick={() => setActiveTab("json")}
              >
                JSON
              </button>
            </div>
          </div>

          <Presets
            onSelectPreset={handleSelectPreset}
            onAutoSubmit={handleAutoSubmit}
          />

          <div className="panel-body">
            {activeTab === "form" ? (
              <ClaimForm
                formData={formData}
                onChange={setFormData}
                onSubmit={() => executePrediction(formData)}
                isLoading={isLoading}
              />
            ) : (
              <JsonUploader
                initialJson={formData}
                onSubmitJson={(parsedClaim) => {
                  setFormData(parsedClaim);
                  executePrediction(parsedClaim);
                }}
                isLoading={isLoading}
              />
            )}
          </div>
        </section>

        {/* Right: triage result */}
        <ResultsDashboard result={result} isLoading={isLoading} error={error} />
      </div>
    </main>
  );
}
