"use client";

import { InvestigationSummary } from "@/lib/api";
import Link from "next/link";
import RiskBadge from "./RiskBadge";

interface InvestigationCardProps {
  investigation: InvestigationSummary;
  isSelected?: boolean;
  onSelect?: (id: string, checked: boolean) => void;
  onDelete?: (id: string) => void;
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending", color: "#6b7280" },
  processing: { label: "Processing", color: "#3b82f6" },
  completed: { label: "Completed", color: "#10b981" },
  failed: { label: "Failed", color: "#ef4444" },
};

const TYPE_ICONS: Record<string, string> = {
  video: "🎬",
  image: "🖼️",
  email: "📧",
  website: "🌐",
};

export default function InvestigationCard({
  investigation: inv,
  isSelected = false,
  onSelect,
  onDelete,
}: InvestigationCardProps) {
  const statusConf = STATUS_CONFIG[inv.status] || STATUS_CONFIG.pending;
  const icon = TYPE_ICONS[inv.type || ""] || "📄";

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div style={{ position: "relative" }}>
      {/* Selection Checkbox Container */}
      {onSelect && (
        <div
          style={{
            position: "absolute",
            top: 14,
            left: 14,
            zIndex: 10,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => onSelect(inv.id, e.target.checked)}
            style={{
              width: 18,
              height: 18,
              cursor: "pointer",
              accentColor: "#a78bfa",
            }}
          />
        </div>
      )}

      {/* Delete Trigger Button */}
      {onDelete && (
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete(inv.id);
          }}
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            zIndex: 10,
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            borderRadius: "50%",
            width: 28,
            height: 28,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            color: "#f87171",
            transition: "all 0.2s",
            fontSize: 13,
          }}
          title="Delete Investigation"
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(239, 68, 68, 0.25)";
            e.currentTarget.style.borderColor = "#ef4444";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)";
            e.currentTarget.style.borderColor = "rgba(239, 68, 68, 0.2)";
          }}
        >
          🗑️
        </button>
      )}

      <Link
        href={`/investigate/${inv.id}`}
        className="investigation-card"
        style={{
          paddingLeft: onSelect ? 46 : undefined,
          border: isSelected ? "1px solid #a78bfa" : undefined,
          boxShadow: isSelected ? "0 0 12px rgba(167, 139, 250, 0.2)" : undefined,
        }}
      >
        <div className="card-header">
          <span className="card-type-icon">{icon}</span>
          <span
            className="card-status"
            style={{ color: statusConf.color }}
          >
            {inv.status === "processing" && (
              <span className="status-dot-animate" />
            )}
            {statusConf.label}
          </span>
        </div>

        <h3 className="card-title">{inv.title}</h3>

        <div className="card-meta">
          <span className="card-date">{formatDate(inv.created_at)}</span>
          {inv.type && (
            <span className="card-type">{inv.type.toUpperCase()}</span>
          )}
        </div>

        <div className="card-footer">
          {inv.trust_score !== null && inv.trust_score !== undefined ? (
            <div className="card-score-row">
              <div className="card-score">
                <span
                  className="card-score-value"
                  style={{
                    color:
                      inv.trust_score >= 80
                        ? "#10b981"
                        : inv.trust_score >= 60
                          ? "#f59e0b"
                          : inv.trust_score >= 40
                            ? "#f97316"
                            : "#ef4444",
                  }}
                >
                  {Math.round(inv.trust_score)}
                </span>
                <span className="card-score-unit">/100</span>
              </div>
              {inv.risk_level && (
                <RiskBadge level={inv.risk_level} size="sm" />
              )}
            </div>
          ) : (
            <div className="card-no-score">
              {inv.status === "processing"
                ? "Analyzing..."
                : inv.status === "failed"
                  ? "Analysis failed"
                  : "Awaiting analysis"}
            </div>
          )}
        </div>
      </Link>
    </div>
  );
}
