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
    <header className="masthead">
      <div>
        <h1>Claim Fraud &amp; Rejection Review</h1>
        <p>openIMIS claim triage — LightGBM scoring with TreeSHAP explanations</p>
      </div>

      <div className="masthead-meta">
        {health && (
          <div className="metric-inline">
            <div>
              <span className="eyebrow">ROC-AUC</span>
              <b>{health.roc_auc_test.toFixed(3)}</b>
            </div>
            <div>
              <span className="eyebrow">Alert cutoff</span>
              <b>{(health.decision_threshold * 100).toFixed(1)}%</b>
            </div>
            <div>
              <span className="eyebrow">Features</span>
              <b>{health.num_features}</b>
            </div>
          </div>
        )}

        <div className={`status-line ${isOnline ? "" : "offline"}`}>
          <span className="status-dot" />
          <span>{isOnline ? "Service online" : "Service offline"}</span>
        </div>

        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="btn"
        >
          API reference
        </a>
      </div>
    </header>
  );
}
