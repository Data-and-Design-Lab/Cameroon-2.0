"use client";

import React, { useEffect, useState } from "react";
import { HealthStatus } from "../types";

interface HeaderProps {
  apiUrl: string;
}

export default function Header({ apiUrl }: HeaderProps) {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    async function timedFetch(url: string): Promise<Response | null> {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      try {
        const res = await fetch(url, { signal: controller.signal, cache: "no-store" });
        clearTimeout(timeout);
        return res.ok ? res : null;
      } catch {
        clearTimeout(timeout);
        return null;
      }
    }

    async function checkHealth() {
      // Try direct connection first (most reliable indicator)
      let res = await timedFetch("http://127.0.0.1:8000/health");
      // Fallback to proxy
      if (!res) {
        res = await timedFetch(`${apiUrl}/health`);
      }

      if (!isMounted) return;

      if (res) {
        try {
          const data = await res.json();
          setHealth(data);
          setIsOnline(true);
        } catch {
          setHealth(null);
          setIsOnline(false);
        }
      } else {
        setHealth(null);
        setIsOnline(false);
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [apiUrl]);

  return (
    <header className="header-card">
      <div className="brand-section">
        <div className="brand-icon" aria-hidden="true">
          FV
        </div>
        <div>
          <h1 className="brand-title">openIMIS Claim Fraud Verifier</h1>
          <p className="brand-subtitle">
            LightGBM Microservice (Leakage-Free GBDT) • Real-Time TreeSHAP Triage
          </p>
        </div>
      </div>

      <div className="header-status">
        <div className={`status-badge ${isOnline ? "online" : "offline"}`}>
          <span className="status-dot" />
          <span>{isOnline ? "Backend Connected (127.0.0.1:8000)" : "Backend Offline"}</span>
        </div>

        {health && (
          <div
            style={{
              fontSize: "0.78rem",
              color: "var(--text-dim)",
              background: "#f1f5f9",
              padding: "0.35rem 0.75rem",
              borderRadius: "6px",
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            ROC-AUC: <strong>{health.roc_auc_test.toFixed(4)}</strong> | Threshold:{" "}
            <strong>{(health.decision_threshold * 100).toFixed(1)}%</strong>
          </div>
        )}

        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="preset-btn"
          style={{ textDecoration: "none" }}
        >
          API Docs
        </a>
      </div>
    </header>
  );
}
