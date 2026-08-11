"use client";

import { useState } from "react";
import { Claim } from "@/lib/api";
import { CheckCircle2, AlertTriangle, ShieldAlert, Sparkles, Filter } from "lucide-react";

interface TextInspectorProps {
  text: string;
  claims: Claim[];
}

export default function TextInspector({ text, claims }: TextInspectorProps) {
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("all");

  if (!text) {
    return (
      <div style={{ color: "var(--text-muted)", fontStyle: "italic", fontSize: 13, padding: 16 }}>
        No extracted text available for this audit.
      </div>
    );
  }

  const activeClaim = claims.find((c) => c.id === activeClaimId);
  const categories = Array.from(new Set(claims.map((c) => c.category || "Uncategorized")));

  const filteredClaims = filterCategory === "all"
    ? claims
    : claims.filter((c) => (c.category || "Uncategorized") === filterCategory);

  const getClaimStyle = (claim: Claim, isActive: boolean) => {
    const isHighConf = claim.confidence >= 0.8;
    const isMediumConf = claim.confidence >= 0.5;
    
    if (isActive) {
      return {
        background: "var(--accent-purple)",
        color: "#ffffff",
        border: "1px solid var(--accent-purple)",
      };
    }

    if (isHighConf) {
      return {
        background: "rgba(16, 185, 129, 0.12)",
        color: "#10b981",
        border: "1px solid rgba(16, 185, 129, 0.3)",
      };
    } else if (isMediumConf) {
      return {
        background: "rgba(245, 158, 11, 0.12)",
        color: "#f59e0b",
        border: "1px solid rgba(245, 158, 11, 0.3)",
      };
    } else {
      return {
        background: "rgba(239, 68, 68, 0.12)",
        color: "#fca5a5",
        border: "1px solid rgba(239, 68, 68, 0.3)",
      };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Category Filter Toolbar */}
      {categories.length > 1 && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 4, fontWeight: 600 }}>
            <Filter size={13} /> Filter Category:
          </span>
          <button
            onClick={() => setFilterCategory("all")}
            className={`btn ${filterCategory === "all" ? "btn-primary" : "btn-secondary"}`}
            style={{ padding: "4px 10px", fontSize: 11 }}
          >
            All ({claims.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`btn ${filterCategory === cat ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "4px 10px", fontSize: 11 }}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {/* Formatted Extracted Text Area */}
      <div className="inspector-text-box">
        <div className="inspector-box-header">
          <Sparkles size={14} className="icon-cyan" />
          <span>Extracted Communication Transcript</span>
        </div>
        <div className="inspector-box-content">
          {text}
        </div>
      </div>

      {/* Active Claim Tooltip Panel */}
      {activeClaim && (
        <div className="active-claim-banner">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
            <div>
              <div className="active-claim-title">
                🎯 {activeClaim.subject} <span>{activeClaim.predicate}</span> {activeClaim.object}
              </div>
              <div className="active-claim-meta">
                <span>Category: <strong>{activeClaim.category || "General"}</strong></span>
                <span>Confidence Score: <strong>{Math.round(activeClaim.confidence * 100)}%</strong></span>
                <span>Evidence Items: <strong>{activeClaim.evidence?.length || 0}</strong></span>
              </div>
            </div>
            <button
              onClick={() => setActiveClaimId(null)}
              className="btn btn-secondary"
              style={{ padding: "4px 8px", fontSize: 11 }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Color-Coded Claims Chips */}
      {filteredClaims.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Extracted Claim Triples (Click to Inspect)
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {filteredClaims.map((claim) => {
              const isActive = activeClaimId === claim.id;
              const style = getClaimStyle(claim, isActive);
              return (
                <button
                  key={claim.id}
                  onClick={() => setActiveClaimId(isActive ? null : claim.id)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: "var(--radius-sm)",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    ...style,
                  }}
                >
                  <span>{claim.subject}</span>
                  <span style={{ opacity: 0.7, fontWeight: 400 }}>{claim.predicate}</span>
                  <span>{claim.object}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
