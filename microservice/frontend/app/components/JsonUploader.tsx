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
  const [fileName, setFileName] = useState<string | null>(null);

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
      setParseError(err.message);
    }
  };

  const handleFileDrop = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const parsed = JSON.parse(text);
        setJsonString(JSON.stringify(parsed, null, 2));
        setFileName(file.name);
        setParseError(null);
      } catch (err: any) {
        setFileName(file.name);
        setParseError(`Could not read ${file.name} as JSON — ${err.message}`);
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
      setParseError(err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <button
        type="button"
        className={`dropzone ${isDragOver ? "is-active" : ""}`}
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
        <strong>
          {fileName ? `Loaded ${fileName}` : "Drop a claim JSON file here"}
        </strong>
        <span>or click to choose a file from your computer</span>
      </button>

      <input
        id="file-input"
        type="file"
        accept=".json,application/json"
        hidden
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            handleFileDrop(e.target.files[0]);
          }
        }}
      />

      <div className="editor-head">
        <label htmlFor="json-editor" className="eyebrow">
          Claim payload
        </label>
        <button
          type="button"
          className="btn btn-quiet"
          onClick={() => {
            try {
              setJsonString(JSON.stringify(JSON.parse(jsonString), null, 2));
              setParseError(null);
            } catch {
              /* keep the user's text as-is when it cannot be parsed */
            }
          }}
        >
          Reformat
        </button>
      </div>

      <textarea
        id="json-editor"
        className="code-area"
        value={jsonString}
        onChange={handleTextChange}
        placeholder="Paste an openIMIS claim payload"
        spellCheck={false}
      />

      {parseError && (
        <div className="notice alert">
          <strong>Invalid JSON</strong>
          {parseError}
        </div>
      )}

      <div className="form-footer">
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading || Boolean(parseError)}
        >
          {isLoading && <span className="spinner" />}
          <span>{isLoading ? "Scoring claim" : "Run risk check"}</span>
        </button>
        <p className="caption">
          The payload is sent to the scoring service exactly as shown above.
        </p>
      </div>
    </form>
  );
}
