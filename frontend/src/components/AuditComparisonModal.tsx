"use client";

import React from "react";
import { InvestigationSummary } from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";
import { X, Scale } from "lucide-react";

interface AuditComparisonModalProps {
  investigations: InvestigationSummary[];
  onClose: () => void;
}

export default function AuditComparisonModal({
  investigations,
  onClose,
}: AuditComparisonModalProps) {
  if (investigations.length === 0) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-container">
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Scale size={22} className="icon-purple" />
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>
                Multi-Audit Benchmark & Risk Comparison
              </h2>
              <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>
                Comparing {investigations.length} selected financial communications
              </p>
            </div>
          </div>
          <button onClick={onClose} className="modal-close-btn" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* Content Table / Grid */}
        <div className="modal-body">
          <div className="comparison-grid" style={{ gridTemplateColumns: `180px repeat(${investigations.length}, minmax(220px, 1fr))` }}>
            {/* Metric Labels Column */}
            <div className="comparison-col headers-col">
              <div className="comparison-cell header-cell">Feature Metric</div>
              <div className="comparison-cell label-cell">Media Channel</div>
              <div className="comparison-cell label-cell">Audit Status</div>
              <div className="comparison-cell label-cell">Risk Level</div>
              <div className="comparison-cell label-cell">Trust Score</div>
              <div className="comparison-cell label-cell">Created Date</div>
            </div>

            {/* Audit Data Columns */}
            {investigations.map((inv) => (
              <div key={inv.id} className="comparison-col data-col">
                <div className="comparison-cell header-cell title-cell">
                  <div className="audit-title" title={inv.title}>{inv.title}</div>
                  <div className="audit-id">ID: {inv.id.substring(0, 8)}...</div>
                </div>

                <div className="comparison-cell">
                  <span className="channel-tag">{(inv.type || "GENERAL").toUpperCase()}</span>
                </div>

                <div className="comparison-cell">
                  <span className={`status-pill ${inv.status}`}>
                    {inv.status}
                  </span>
                </div>

                <div className="comparison-cell">
                  <RiskBadge level={inv.risk_level} />
                </div>

                <div className="comparison-cell">
                  <div className="score-box" style={{
                    color: inv.trust_score != null
                      ? inv.trust_score >= 80 ? "#10b981" : inv.trust_score >= 60 ? "#f59e0b" : "#ef4444"
                      : "var(--text-muted)"
                  }}>
                    {inv.trust_score != null ? `${inv.trust_score}/100` : "—"}
                  </div>
                </div>

                <div className="comparison-cell font-mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {new Date(inv.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-primary" style={{ padding: "8px 20px" }}>
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  );
}
