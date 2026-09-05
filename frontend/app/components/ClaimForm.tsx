"use client";

import React from "react";
import { ClaimInput } from "../types";

interface ClaimFormProps {
  formData: ClaimInput;
  onChange: (data: ClaimInput) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

export default function ClaimForm({
  formData,
  onChange,
  onSubmit,
  isLoading,
}: ClaimFormProps) {
  const updateField = (field: keyof ClaimInput, value: any) => {
    onChange({
      ...formData,
      [field]: value,
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* 1. Claim Financials & Timing */}
      <div className="form-section">
        <div className="form-section-title">
          <span>1. Claim Financials & Timing</span>
        </div>
        <div className="form-grid-2">
          <div className="form-group">
            <label htmlFor="claimed_amount">Claimed Amount (FCFA) *</label>
            <input
              id="claimed_amount"
              type="number"
              min="0"
              step="100"
              required
              value={formData.claimed_amount || ""}
              onChange={(e) => updateField("claimed_amount", parseFloat(e.target.value) || 0)}
              placeholder="e.g. 15000"
            />
          </div>
          <div className="form-group">
            <label htmlFor="claim_id">Claim Tracking ID (Optional)</label>
            <input
              id="claim_id"
              type="text"
              value={formData.claim_id || ""}
              onChange={(e) => updateField("claim_id", e.target.value)}
              placeholder="e.g. CLM-2026-001"
            />
          </div>
        </div>

        <div className="form-grid-3" style={{ marginTop: "0.85rem" }}>
          <div className="form-group">
            <label htmlFor="date_from">Service Start (DateFrom) *</label>
            <input
              id="date_from"
              type="date"
              required
              value={formData.date_from || ""}
              onChange={(e) => updateField("date_from", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="date_to">Service End (DateTo) *</label>
            <input
              id="date_to"
              type="date"
              required
              value={formData.date_to || ""}
              onChange={(e) => updateField("date_to", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="date_claimed">Submission Date</label>
            <input
              id="date_claimed"
              type="date"
              value={formData.date_claimed || ""}
              onChange={(e) => updateField("date_claimed", e.target.value)}
            />
          </div>
        </div>

        <div className="form-grid-3" style={{ marginTop: "0.85rem" }}>
          <div className="form-group">
            <label htmlFor="care_type">Care Setting</label>
            <select
              id="care_type"
              value={formData.care_type}
              onChange={(e) => updateField("care_type", e.target.value)}
            >
              <option value="OPD">OPD (Outpatient)</option>
              <option value="IPD">IPD (Inpatient)</option>
              <option value="UNK">Unknown / Other</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="visit_type">Visit Urgency</label>
            <select
              id="visit_type"
              value={formData.visit_type}
              onChange={(e) => updateField("visit_type", e.target.value)}
            >
              <option value="O">Ordinary (Routine)</option>
              <option value="E">Emergency</option>
              <option value="R">Referral</option>
              <option value="UNK">Unknown</option>
            </select>
          </div>
          <div className="form-group" style={{ justifyContent: "center" }}>
            <label className="checkbox-group" htmlFor="has_explanation">
              <input
                id="has_explanation"
                type="checkbox"
                checked={Boolean(formData.has_explanation)}
                onChange={(e) => updateField("has_explanation", e.target.checked)}
              />
              <span>Written Justification Attached</span>
            </label>
          </div>
        </div>
      </div>

      {/* 2. Services & Tariffs */}
      <div className="form-section">
        <div className="form-section-title">
          <span>2. Services & Fee Tariffs</span>
        </div>
        <div className="form-grid-2">
          <div className="form-group">
            <label htmlFor="service_lines_count">Service Lines Count</label>
            <input
              id="service_lines_count"
              type="number"
              min="0"
              value={formData.service_lines_count ?? 1}
              onChange={(e) => updateField("service_lines_count", parseInt(e.target.value, 10) || 0)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="service_tariff_total">Official Tariff Schedule Total (FCFA)</label>
            <input
              id="service_tariff_total"
              type="number"
              min="0"
              value={formData.service_tariff_total ?? ""}
              onChange={(e) => updateField("service_tariff_total", parseFloat(e.target.value) || 0)}
              placeholder="Expected catalogue price"
            />
          </div>
        </div>

        <div className="form-grid-2" style={{ marginTop: "0.85rem" }}>
          <div className="form-group">
            <label htmlFor="service_asked_total">Total Billed Across Services (FCFA)</label>
            <input
              id="service_asked_total"
              type="number"
              min="0"
              value={formData.service_asked_total ?? ""}
              onChange={(e) => updateField("service_asked_total", parseFloat(e.target.value) || 0)}
              placeholder="Sum of service items"
            />
          </div>
          <div className="form-group">
            <label htmlFor="service_tariff_breaches">Tariff Limit Breaches</label>
            <input
              id="service_tariff_breaches"
              type="number"
              min="0"
              value={formData.service_tariff_breaches ?? 0}
              onChange={(e) => updateField("service_tariff_breaches", parseInt(e.target.value, 10) || 0)}
              placeholder="Lines exceeding statutory limit"
            />
          </div>
        </div>
      </div>

      {/* 3. Insurance Policy (Point-in-Time) */}
      <div className="form-section">
        <div className="form-section-title">
          <span>3. Insurance Policy (Point-in-Time Validity)</span>
        </div>
        <div className="form-grid-3">
          <div className="form-group">
            <label htmlFor="policy_start_date">Policy Start Date</label>
            <input
              id="policy_start_date"
              type="date"
              value={formData.policy_start_date || ""}
              onChange={(e) => updateField("policy_start_date", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="policy_expiry_date">Policy Expiry Date</label>
            <input
              id="policy_expiry_date"
              type="date"
              value={formData.policy_expiry_date || ""}
              onChange={(e) => updateField("policy_expiry_date", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="policy_enrollment_date">Enrollment Date</label>
            <input
              id="policy_enrollment_date"
              type="date"
              value={formData.policy_enrollment_date || ""}
              onChange={(e) => updateField("policy_enrollment_date", e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* 4. Provider & Diagnosis */}
      <div className="form-section">
        <div className="form-section-title">
          <span>4. Provider Facility & Diagnosis</span>
        </div>
        <div className="form-grid-3">
          <div className="form-group">
            <label htmlFor="hfid">Health Facility ID</label>
            <input
              id="hfid"
              type="number"
              value={formData.hfid ?? 404}
              onChange={(e) => updateField("hfid", parseInt(e.target.value, 10) || 404)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="geo_region">Region</label>
            <select
              id="geo_region"
              value={formData.geo_region}
              onChange={(e) => updateField("geo_region", e.target.value)}
            >
              <option value="Centre">Centre</option>
              <option value="Littoral">Littoral</option>
              <option value="Nord">Nord</option>
              <option value="Extreme Nord">Extreme Nord</option>
              <option value="Adamaoua">Adamaoua</option>
              <option value="Ouest">Ouest</option>
              <option value="South West">South West</option>
              <option value="North West">North West</option>
              <option value="Est">Est</option>
              <option value="Sud">Sud</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="geo_district">Health District</label>
            <input
              id="geo_district"
              type="text"
              value={formData.geo_district || "Guider"}
              onChange={(e) => updateField("geo_district", e.target.value)}
            />
          </div>
        </div>

        <div className="form-grid-2" style={{ marginTop: "0.85rem" }}>
          <div className="form-group">
            <label htmlFor="icdid">Primary ICD Diagnosis ID</label>
            <input
              id="icdid"
              type="number"
              value={formData.icdid ?? 1931}
              onChange={(e) => updateField("icdid", parseInt(e.target.value, 10) || 1931)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="dx_chapter">ICD-10 Chapter Letter</label>
            <select
              id="dx_chapter"
              value={formData.dx_chapter || "J"}
              onChange={(e) => updateField("dx_chapter", e.target.value)}
            >
              <option value="A">A - Infectious & Parasitic</option>
              <option value="B">B - Other Infections</option>
              <option value="J">J - Respiratory System</option>
              <option value="K">K - Digestive System</option>
              <option value="Q">Q - Congenital Malformations</option>
              <option value="G">G - Nervous System</option>
              <option value="N">N - Genitourinary</option>
              <option value="P">P - Perinatal Conditions</option>
              <option value="UNK">UNK - Unknown</option>
            </select>
          </div>
        </div>
      </div>

      <button type="submit" className="submit-btn" disabled={isLoading}>
        {isLoading ? (
          <>
            <span className="spinner" />
            <span>Evaluating Claim with LightGBM & TreeSHAP...</span>
          </>
        ) : (
          <>
            <span>Verify Claim for Fraud Risk</span>
          </>
        )}
      </button>
    </form>
  );
}
