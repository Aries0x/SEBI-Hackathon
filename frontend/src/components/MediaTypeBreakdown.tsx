"use client";

import { InvestigationSummary } from "@/lib/api";

interface MediaTypeBreakdownProps {
  investigations: InvestigationSummary[];
}

const MEDIA_CONFIG: Record<
  string,
  { icon: string; label: string; gradient: string; color: string }
> = {
  video: {
    icon: "🎬",
    label: "Video",
    gradient: "linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(139, 92, 246, 0.05))",
    color: "#8b5cf6",
  },
  image: {
    icon: "🖼️",
    label: "Image",
    gradient: "linear-gradient(135deg, rgba(6, 182, 212, 0.15), rgba(6, 182, 212, 0.05))",
    color: "#06b6d4",
  },
  email: {
    icon: "📧",
    label: "Email",
    gradient: "linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05))",
    color: "#f59e0b",
  },
  website: {
    icon: "🌐",
    label: "Website",
    gradient: "linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05))",
    color: "#3b82f6",
  },
};

export default function MediaTypeBreakdown({
  investigations,
}: MediaTypeBreakdownProps) {
  const total = investigations.length;
  if (total === 0) return null;

  const typeCounts: Record<string, { count: number; threats: number }> = {};
  for (const inv of investigations) {
    const type = inv.type || "unknown";
    if (!typeCounts[type]) typeCounts[type] = { count: 0, threats: 0 };
    typeCounts[type].count++;
    if (inv.risk_level === "critical" || inv.risk_level === "high") {
      typeCounts[type].threats++;
    }
  }

  const types = ["video", "image", "email", "website"];

  return (
    <div className="media-breakdown-card">
      <div className="media-breakdown-header">
        <h3>
          <span style={{ marginRight: 8 }}>📱</span>
          Media Type Analysis
        </h3>
      </div>
      <div className="media-breakdown-grid">
        {types.map((type) => {
          const conf = MEDIA_CONFIG[type];
          const data = typeCounts[type] || { count: 0, threats: 0 };
          const percentage = total > 0 ? (data.count / total) * 100 : 0;

          return (
            <div
              key={type}
              className="media-breakdown-item"
              style={{
                background: conf.gradient,
                borderColor: `${conf.color}33`,
              }}
            >
              <div className="media-breakdown-icon-row">
                <span className="media-breakdown-icon">{conf.icon}</span>
                {/* Mini circular progress ring */}
                <svg
                  width="36"
                  height="36"
                  viewBox="0 0 36 36"
                  className="media-breakdown-ring"
                >
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="rgba(255,255,255,0.06)"
                    strokeWidth="3"
                  />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke={conf.color}
                    strokeWidth="3"
                    strokeDasharray={`${(percentage / 100) * 87.96} 87.96`}
                    strokeDashoffset="0"
                    strokeLinecap="round"
                    transform="rotate(-90 18 18)"
                    style={{
                      transition: "stroke-dasharray 1s cubic-bezier(0.4, 0, 0.2, 1)",
                    }}
                  />
                  <text
                    x="18"
                    y="18"
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill={conf.color}
                    fontSize="8"
                    fontWeight="800"
                  >
                    {Math.round(percentage)}%
                  </text>
                </svg>
              </div>
              <div className="media-breakdown-label">{conf.label}</div>
              <div className="media-breakdown-count">{data.count}</div>
              {data.threats > 0 && (
                <div
                  className="media-breakdown-threat"
                  style={{ color: "#ef4444" }}
                >
                  ⚠ {data.threats} threat{data.threats > 1 ? "s" : ""}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
