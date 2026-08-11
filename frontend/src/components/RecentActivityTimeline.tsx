"use client";

import { InvestigationSummary } from "@/lib/api";

interface RecentActivityTimelineProps {
  investigations: InvestigationSummary[];
}

const STATUS_ICONS: Record<string, { icon: string; color: string; label: string }> = {
  completed: { icon: "✅", color: "#10b981", label: "Analysis Complete" },
  processing: { icon: "⏳", color: "#3b82f6", label: "Processing" },
  pending: { icon: "📋", color: "#6b7280", label: "New Investigation" },
  failed: { icon: "❌", color: "#ef4444", label: "Analysis Failed" },
};

const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#10b981",
};

export default function RecentActivityTimeline({
  investigations,
}: RecentActivityTimelineProps) {
  // Take the most recently updated 5 items
  const recentItems = [...investigations]
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )
    .slice(0, 5);

  if (recentItems.length === 0) return null;

  const formatRelativeTime = (dateStr: string) => {
    const now = new Date();
    const then = new Date(dateStr);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return then.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  };

  return (
    <div className="timeline-card">
      <div className="timeline-header">
        <h3>
          <span style={{ marginRight: 8 }}>🕐</span>
          Recent Activity
        </h3>
        <span className="timeline-live-dot" />
      </div>

      <div className="timeline-list">
        {recentItems.map((inv, idx) => {
          const statusConf = STATUS_ICONS[inv.status] || STATUS_ICONS.pending;
          const isCritical =
            inv.risk_level === "critical" || inv.risk_level === "high";
          const riskColor = RISK_COLORS[inv.risk_level || ""] || undefined;

          return (
            <div
              key={inv.id}
              className="timeline-item"
              style={{
                animationDelay: `${idx * 0.08}s`,
              }}
            >
              {/* Connector Line */}
              {idx < recentItems.length - 1 && (
                <div
                  className="timeline-connector"
                  style={{
                    backgroundColor:
                      inv.status === "completed"
                        ? statusConf.color + "44"
                        : "var(--border)",
                  }}
                />
              )}

              {/* Status Icon */}
              <div
                className="timeline-icon"
                style={{
                  borderColor: statusConf.color,
                  boxShadow: `0 0 10px ${statusConf.color}33`,
                }}
              >
                <span style={{ fontSize: 14 }}>{statusConf.icon}</span>
              </div>

              {/* Content */}
              <div className="timeline-content">
                <div className="timeline-content-top">
                  <span className="timeline-title">
                    {inv.title.length > 45
                      ? inv.title.substring(0, 45) + "…"
                      : inv.title}
                  </span>
                  <span className="timeline-time">
                    {formatRelativeTime(inv.updated_at)}
                  </span>
                </div>
                <div className="timeline-content-bottom">
                  <span
                    className="timeline-status-badge"
                    style={{
                      color: statusConf.color,
                      backgroundColor: statusConf.color + "18",
                    }}
                  >
                    {statusConf.label}
                  </span>
                  {inv.trust_score != null && (
                    <span
                      className="timeline-score"
                      style={{
                        color:
                          inv.trust_score >= 80
                            ? "#10b981"
                            : inv.trust_score >= 60
                              ? "#f59e0b"
                              : "#ef4444",
                      }}
                    >
                      Score: {Math.round(inv.trust_score)}
                    </span>
                  )}
                  {isCritical && riskColor && (
                    <span
                      className="timeline-threat-tag"
                      style={{
                        color: riskColor,
                        backgroundColor: riskColor + "18",
                        borderColor: riskColor + "33",
                      }}
                    >
                      🚨 {inv.risk_level?.toUpperCase()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
