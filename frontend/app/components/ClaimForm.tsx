"use client";

import React from "react";
import { ClaimInput } from "../types";

interface ClaimFormProps {
  formData: ClaimInput;
  onChange: (data: ClaimInput) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

const REGIONS = [
  "Centre",
  "Littoral",
  "Nord",
  "Extreme Nord",
  "Adamaoua",
  "Ouest",
  "South West",
  "North West",
  "Est",
  "Sud",
];

const DX_CHAPTERS: { value: string; label: string }[] = [
  { value: "A", label: "A — Infectious & parasitic" },
  { value: "B", label: "B — Other infections" },
  { value: "G", label: "G — Nervous system" },
  { value: "J", label: "J — Respiratory system" },
  { value: "K", label: "K — Digestive system" },
  { value: "N", label: "N — Genitourinary" },
  { value: "P", label: "P — Perinatal conditions" },
  { value: "Q", label: "Q — Congenital malformations" },
  { value: "UNK", label: "Unknown" },
];

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

  const numberField = (
    field: keyof ClaimInput,
    label: string,
    opts: { step?: string; hint?: string; placeholder?: string } = {}
  ) => (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      <input
        id={field}
        type="number"
        min="0"
        step={opts.step ?? "any"}
        value={(formData[field] as number | undefined) ?? ""}
        onChange={(e) => updateField(field, parseFloat(e.target.value) || 0)}
        placeholder={opts.placeholder}
      />
      {opts.hint && <span className="field-hint">{opts.hint}</span>}
    </div>
  );

  const dateField = (field: keyof ClaimInput, label: string, required = false) => (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      <input
        id={field}
        type="date"
        required={required}
        value={(formData[field] as string | undefined) || ""}
        onChange={(e) => updateField(field, e.target.value)}
      />
    </div>
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Claim basics */}
      <fieldset className="fieldset">
        <legend>Claim</legend>
        <p className="fieldset-note">
          Amount billed to the scheme and the period of care it covers.
        </p>

        <div className="field-grid">
          <div className="field">
            <label htmlFor="claimed_amount">Claimed amount (FCFA)</label>
            <input
              id="claimed_amount"
              type="number"
              min="0"
              step="100"
              required
              value={formData.claimed_amount || ""}
              onChange={(e) =>
                updateField("claimed_amount", parseFloat(e.target.value) || 0)
              }
              placeholder="15000"
            />
          </div>
          <div className="field">
            <label htmlFor="claim_id">Claim reference</label>
            <input
              id="claim_id"
              type="text"
              value={formData.claim_id || ""}
              onChange={(e) => updateField("claim_id", e.target.value)}
              placeholder="CLM-2026-001"
            />
          </div>

          {dateField("date_from", "Service start", true)}
          {dateField("date_to", "Service end", true)}
          {dateField("date_claimed", "Submitted on")}

          <div className="field">
            <label htmlFor="care_type">Care setting</label>
            <select
              id="care_type"
              value={formData.care_type}
              onChange={(e) => updateField("care_type", e.target.value)}
            >
              <option value="OPD">Outpatient</option>
              <option value="IPD">Inpatient</option>
              <option value="UNK">Unknown</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="visit_type">Visit type</label>
            <select
              id="visit_type"
              value={formData.visit_type}
              onChange={(e) => updateField("visit_type", e.target.value)}
            >
              <option value="O">Ordinary</option>
              <option value="E">Emergency</option>
              <option value="R">Referral</option>
              <option value="UNK">Unknown</option>
            </select>
          </div>
          <label className="switch-field" htmlFor="has_explanation">
            <input
              id="has_explanation"
              type="checkbox"
              checked={Boolean(formData.has_explanation)}
              onChange={(e) => updateField("has_explanation", e.target.checked)}
            />
            <span>Justification attached</span>
          </label>
        </div>
      </fieldset>

      {/* Services and tariffs */}
      <fieldset className="fieldset">
        <legend>Services &amp; tariffs</legend>
        <p className="fieldset-note">
          Billed totals against the official fee schedule. Gaps here drive most
          rejections.
        </p>

        <div className="field-grid">
          {numberField("service_lines_count", "Service lines", { step: "1" })}
          {numberField("service_tariff_total", "Tariff total (FCFA)", {
            placeholder: "Catalogue price",
          })}
          {numberField("service_asked_total", "Billed total (FCFA)", {
            placeholder: "Sum of lines",
          })}
          {numberField("service_tariff_breaches", "Tariff breaches", {
            step: "1",
            hint: "Lines above the statutory limit.",
          })}
        </div>
      </fieldset>

      {/* Policy */}
      <fieldset className="fieldset">
        <legend>Policy validity</legend>
        <p className="fieldset-note">
          Cover is checked as at the service date, not at submission.
        </p>

        <div className="field-grid">
          {dateField("policy_start_date", "Policy start")}
          {dateField("policy_expiry_date", "Policy expiry")}
          {dateField("policy_enrollment_date", "Enrolment")}
        </div>
      </fieldset>

      {/* Provider and diagnosis */}
      <fieldset className="fieldset">
        <legend>Provider &amp; diagnosis</legend>
        <p className="fieldset-note">
          Facility identity and the primary coded diagnosis.
        </p>

        <div className="field-grid">
          <div className="field">
            <label htmlFor="hfid">Facility ID</label>
            <input
              id="hfid"
              type="number"
              value={formData.hfid ?? 404}
              onChange={(e) =>
                updateField("hfid", parseInt(e.target.value, 10) || 404)
              }
            />
          </div>
          <div className="field">
            <label htmlFor="geo_region">Region</label>
            <select
              id="geo_region"
              value={formData.geo_region}
              onChange={(e) => updateField("geo_region", e.target.value)}
            >
              {REGIONS.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="geo_district">Health district</label>
            <input
              id="geo_district"
              type="text"
              value={formData.geo_district || ""}
              onChange={(e) => updateField("geo_district", e.target.value)}
              placeholder="Guider"
            />
          </div>
          <div className="field">
            <label htmlFor="icdid">Primary ICD code ID</label>
            <input
              id="icdid"
              type="number"
              value={formData.icdid ?? 1931}
              onChange={(e) =>
                updateField("icdid", parseInt(e.target.value, 10) || 1931)
              }
            />
          </div>
          <div className="field span-2">
            <label htmlFor="dx_chapter">ICD-10 chapter</label>
            <select
              id="dx_chapter"
              value={formData.dx_chapter || "J"}
              onChange={(e) => updateField("dx_chapter", e.target.value)}
            >
              {DX_CHAPTERS.map((chapter) => (
                <option key={chapter.value} value={chapter.value}>
                  {chapter.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>

      {/* Advanced */}
      <details className="disclosure">
        <summary>
          Advanced model inputs
          <span className="eyebrow">Optional</span>
        </summary>

        <div className="disclosure-body">
          <p className="fieldset-note">
            Derived service and item aggregates. Leave as loaded unless you are
            reproducing a specific claim.
          </p>

          <div className="field-grid">
            <div className="field">
              <label htmlFor="hf_level">Facility level</label>
              <select
                id="hf_level"
                value={formData.hf_level || "H"}
                onChange={(e) => updateField("hf_level", e.target.value)}
              >
                <option value="D">Dispensary</option>
                <option value="C">Health centre</option>
                <option value="H">Hospital</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="hf_caretype">Facility care type</label>
              <select
                id="hf_caretype"
                value={formData.hf_caretype || "B"}
                onChange={(e) => updateField("hf_caretype", e.target.value)}
              >
                <option value="O">Outpatient only</option>
                <option value="I">Inpatient only</option>
                <option value="B">Both</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="hf_legalform">Legal form</label>
              <select
                id="hf_legalform"
                value={formData.hf_legalform || "G"}
                onChange={(e) => updateField("hf_legalform", e.target.value)}
              >
                <option value="G">Government</option>
                <option value="D">District organisation</option>
                <option value="P">Private</option>
                <option value="C">Charity</option>
              </select>
            </div>

            {numberField("service_asked_mean", "Mean billed per line")}
            {numberField("service_asked_max", "Largest billed line")}
            {numberField("service_n_distinct", "Distinct services", { step: "1" })}
            {numberField("service_tariff_ratio_max", "Max billed / tariff", {
              step: "0.01",
            })}
            {numberField("service_tariff_ratio_mean", "Mean billed / tariff", {
              step: "0.01",
            })}
            {numberField("service_repeat_rate", "Repeat rate", { step: "0.01" })}
            {numberField("service_top_line_share", "Top line share", {
              step: "0.01",
            })}
            {numberField("item_lines_count", "Item lines", { step: "1" })}
            {numberField("item_asked_total", "Items billed (FCFA)")}
          </div>
        </div>
      </details>

      <div className="form-footer">
        <button type="submit" className="btn btn-primary" disabled={isLoading}>
          {isLoading && <span className="spinner" />}
          <span>{isLoading ? "Scoring claim" : "Run risk check"}</span>
        </button>
        <p className="caption">
          Scored against the calibrated LightGBM model, with TreeSHAP attributions
          for each factor.
        </p>
      </div>
    </form>
  );
}
