"use client";

import { useEffect, useState } from "react";
import { InvestigationSummary } from "@/lib/api";

interface RiskDistributionChartProps {
  investigations: InvestigationSummary[];
}

const RISK_CONFIG: Record<string, { label: string; color: string; order: number }> = {
  critical: { label: "Critical", color: "#ef4444", order: 0 },
  high: { label: "High", color: "#f97316", order: 1 },
  medium: { label: "Medium", color: "#f59e0b", order: 2 },
  low: { label: "Low", color: "#10b981", order: 3 },
};

export default function RiskDistributionChart({
  investigations,
}: RiskDistributionChartProps) {
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Count by risk level
  const completed = investigations.filter(
    (i) => i.status === "completed" && i.risk_level
  );
  const total = completed.length;

  if (total === 0) return null;

  const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  completed.forEach((inv) => {
    const level = inv.risk_level?.toLowerCase() || "low";
    if (counts[level] !== undefined) {
      counts[level]++;
    }
  });

  const segments = Object.entries(RISK_CONFIG)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([key, conf]) => ({
      key,
      label: conf.label,
      color: conf.color,
      count: counts[key] || 0,
      percentage: total > 0 ? ((counts[key] || 0) / total) * 100 : 0,
    }))
    .filter((s) => s.count > 0);

  return (
    <div className="risk-distribution-card">
      <div className="risk-dist-header">
        <h3>
          <span style={{ marginRight: 8 }}>📊</span>
          Risk Level Distribution
        </h3>
        <span className="risk-dist-total">{total} analyzed</span>
      </div>

      {/* Stacked Bar */}
      <div className="risk-dist-bar-container">
        <div className="risk-dist-bar">
          {segments.map((seg) => (
            <div
              key={seg.key}
              className="risk-dist-segment"
              style={{
                width: animated ? `${seg.percentage}%` : "0%",
                backgroundColor: seg.color,
                transition: `width 1s cubic-bezier(0.4, 0, 0.2, 1) ${
                  RISK_CONFIG[seg.key].order * 0.15
                }s`,
              }}
              title={`${seg.label}: ${seg.count} (${Math.round(seg.percentage)}%)`}
            />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="risk-dist-legend">
        {segments.map((seg) => (
          <div key={seg.key} className="risk-dist-legend-item">
            <span
              className="risk-dist-dot"
              style={{ backgroundColor: seg.color }}
            />
            <span className="risk-dist-label">{seg.label}</span>
            <span className="risk-dist-count">{seg.count}</span>
            <span className="risk-dist-pct">
              {Math.round(seg.percentage)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
