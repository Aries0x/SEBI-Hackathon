"use client";

import { useState, useRef } from "react";
import { uploadDocument, DocumentUploadResponse } from "@/lib/api";
import { FileText, UploadCloud, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

export default function DocumentUploader() {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<DocumentUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const res = await uploadDocument(file);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to upload and index document");
    } finally {
      setUploading(false);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <div className="doc-upload-section">
      <div className="doc-upload-header">
        <FileText size={18} className="icon-green" />
        <span>Add Knowledge Document to RAG Database</span>
      </div>
      <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 14 }}>
        Upload text documents, SEBI circulars, audit notes, or CSV reports (.txt, .md, .csv, .pdf). They will be automatically chunked and indexed into ChromaDB vector store for RAG AI reasoning.
      </p>

      <div
        className={`doc-upload-zone ${dragActive ? "drag-active" : ""}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".txt,.md,.csv,.pdf,.json"
          onChange={onChange}
          style={{ display: "none" }}
        />

        {uploading ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
            <Loader2 size={32} className="spinner" style={{ border: "none", animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-teal)" }}>
              Chunking & Indexing document into ChromaDB...
            </span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
            <UploadCloud size={36} style={{ color: "var(--accent-teal)" }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
              Click or drag document here to index
            </span>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              Supports TXT, MD, CSV, PDF
            </span>
          </div>
        )}
      </div>

      {result && (
        <div className="doc-upload-success">
          <CheckCircle2 size={18} />
          <span>
            Indexed <strong>{result.filename}</strong> into RAG collection ({result.chunks_indexed} vector chunks ready for chatbot retrieval)!
          </span>
        </div>
      )}

      {error && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", background: "rgba(220, 38, 38, 0.08)", border: "1px solid rgba(220, 38, 38, 0.2)", borderRadius: "var(--radius-sm)", marginTop: 12, fontSize: 13, color: "#dc2626" }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
