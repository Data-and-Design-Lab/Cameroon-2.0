"use client";

import React, { useState } from "react";
import { ClaimInput } from "../types";

interface JsonUploaderProps {
  initialJson: ClaimInput;
  onSubmitJson: (data: ClaimInput) => void;
  isLoading: boolean;
}

export default function JsonUploader({
  initialJson,
  onSubmitJson,
  isLoading,
}: JsonUploaderProps) {
  const [jsonString, setJsonString] = useState<string>(
    JSON.stringify(initialJson, null, 2)
  );
  const [parseError, setParseError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  // Sync if initialJson changes from presets
  React.useEffect(() => {
    setJsonString(JSON.stringify(initialJson, null, 2));
    setParseError(null);
  }, [initialJson]);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setJsonString(val);
    try {
      JSON.parse(val);
      setParseError(null);
    } catch (err: any) {
      setParseError(`JSON Syntax Error: ${err.message}`);
    }
  };

  const handleFileDrop = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const parsed = JSON.parse(text);
        setJsonString(JSON.stringify(parsed, null, 2));
        setParseError(null);
      } catch (err: any) {
        setParseError(`Failed to parse file as JSON: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const parsed = JSON.parse(jsonString);
      setParseError(null);
      onSubmitJson(parsed);
    } catch (err: any) {
      setParseError(`Invalid JSON format: ${err.message}`);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div
        className={`json-dropzone ${isDragOver ? "drag-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileDrop(e.dataTransfer.files[0]);
          }
        }}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".json,application/json"
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileDrop(e.target.files[0]);
            }
          }}
        />
        <div style={{ fontSize: "1.2rem", marginBottom: "0.5rem", fontWeight: 700, color: "var(--text-dim)" }}>JSON</div>
        <p style={{ fontWeight: 600, fontSize: "0.95rem" }}>
          Drag & Drop an openIMIS Claim JSON file here
        </p>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
          or click to browse your computer
        </p>
      </div>

      <div className="form-group" style={{ marginBottom: "1rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.35rem",
          }}
        >
          <label htmlFor="json-editor">Raw JSON Payload Editor</label>
          <button
            type="button"
            className="preset-btn"
            style={{ padding: "0.2rem 0.6rem", fontSize: "0.75rem" }}
            onClick={() => {
              try {
                const parsed = JSON.parse(jsonString);
                setJsonString(JSON.stringify(parsed, null, 2));
                setParseError(null);
              } catch {}
            }}
          >
            Format JSON
          </button>
        </div>

        <textarea
          id="json-editor"
          className="json-textarea"
          value={jsonString}
          onChange={handleTextChange}
          placeholder="Paste openIMIS claim JSON here..."
          spellCheck={false}
        />
      </div>

      {parseError && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            borderRadius: "8px",
            padding: "0.75rem 1rem",
            color: "#fca5a5",
            fontSize: "0.85rem",
            marginBottom: "1rem",
          }}
        >
          {parseError}
        </div>
      )}

      <button
        type="submit"
        className="submit-btn"
        disabled={isLoading || Boolean(parseError)}
      >
        {isLoading ? (
          <>
            <span className="spinner" />
            <span>Posting JSON to Fraud Microservice...</span>
          </>
        ) : (
          <>
            <span>Verify Uploaded Claim JSON</span>
          </>
        )}
      </button>
    </form>
  );
}
