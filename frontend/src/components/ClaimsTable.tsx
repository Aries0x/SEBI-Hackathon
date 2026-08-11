"use client";

import { Claim } from "@/lib/api";
import { Check, X, HelpCircle } from "lucide-react";

interface ClaimsTableProps {
  claims: Claim[];
}

export default function ClaimsTable({ claims }: ClaimsTableProps) {
  if (!claims || claims.length === 0) {
    return (
      <div className="claims-empty">
        <p>No claims extracted yet.</p>
      </div>
    );
  }

  const getStatus = (claim: Claim) => {
    if (!claim.evidence || claim.evidence.length === 0) return "unverified";
    const hasSupport = claim.evidence.some((e) => e.supports && e.confidence > 0.5);
    const hasContradiction = claim.evidence.some(
      (e) => !e.supports && e.confidence > 0.5
    );
    if (hasContradiction) return "contradicted";
    if (hasSupport) return "verified";
    return "unverified";
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "verified":
        return (
          <span
            className="status-badge"
            style={{
              color: "#10b981",
              background: "rgba(16,185,129,0.12)",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Check size={12} /> Verified
          </span>
        );
      case "contradicted":
        return (
          <span
            className="status-badge"
            style={{
              color: "#ef4444",
              background: "rgba(239,68,68,0.12)",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <X size={12} /> Contradicted
          </span>
        );
      default:
        return (
          <span
            className="status-badge"
            style={{
              color: "#6b7280",
              background: "rgba(107,114,128,0.12)",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <HelpCircle size={12} /> Unverified
          </span>
        );
    }
  };

  const statusColors: Record<string, string> = {
    verified: "#10b981",
    contradicted: "#ef4444",
    unverified: "#6b7280",
  };

  const categoryColors: Record<string, string> = {
    financial: "#3b82f6",
    regulatory: "#8b5cf6",
    performance: "#f59e0b",
    identity: "#06b6d4",
    prediction: "#ef4444",
    urgency: "#f97316",
  };

  return (
    <div className="claims-table-wrapper">
      <table className="claims-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Claim</th>
            <th>Category</th>
            <th>Confidence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim, i) => {
            const status = getStatus(claim);
            const color = statusColors[status] || "#6b7280";
            const catColor = categoryColors[claim.category || ""] || "#6b7280";

            return (
              <tr key={claim.id}>
                <td className="claim-index">{i + 1}</td>
                <td className="claim-text">
                  <strong>{claim.subject}</strong> {claim.predicate}{" "}
                  <em>{claim.object}</em>
                  {claim.raw_text && (
                    <div className="claim-raw-text">
                      &quot;{claim.raw_text.substring(0, 120)}
                      {claim.raw_text.length > 120 ? "..." : ""}&quot;
                    </div>
                  )}
                </td>
                <td>
                  <span
                    className="category-badge"
                    style={{
                      color: catColor,
                      background: catColor + "18",
                      border: `1px solid ${catColor}33`,
                    }}
                  >
                    {claim.category || "—"}
                  </span>
                </td>
                <td>
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{
                        width: `${claim.confidence * 100}%`,
                        background: color,
                      }}
                    />
                  </div>
                  <span className="confidence-text">
                    {Math.round(claim.confidence * 100)}%
                  </span>
                </td>
                <td>
                  {getStatusBadge(status)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
