"use client";

import { useEffect, useState } from "react";
import { InvestigationSummary } from "@/lib/api";

interface TrustScoreHistogramProps {
  investigations: InvestigationSummary[];
}

const BUCKETS = [
  { min: 0, max: 20, label: "0–20", tag: "Critical", color: "#ef4444" },
  { min: 20, max: 40, label: "20–40", tag: "High Risk", color: "#f97316" },
  { min: 40, max: 60, label: "40–60", tag: "Medium", color: "#f59e0b" },
  { min: 60, max: 80, label: "60–80", tag: "Caution", color: "#3b82f6" },
  { min: 80, max: 100, label: "80–100", tag: "Safe", color: "#10b981" },
];

export default function TrustScoreHistogram({
  investigations,
}: TrustScoreHistogramProps) {
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 200);
    return () => clearTimeout(timer);
  }, []);

  const scored = investigations.filter(
    (i) => i.trust_score != null && i.status === "completed"
  );

  if (scored.length === 0) return null;

  // Count items per bucket
  const bucketCounts = BUCKETS.map((bucket) => {
    const count = scored.filter(
      (i) =>
        (i.trust_score ?? 0) >= bucket.min &&
        (bucket.max === 100
          ? (i.trust_score ?? 0) <= bucket.max
          : (i.trust_score ?? 0) < bucket.max)
    ).length;
    return { ...bucket, count };
  });

  const maxCount = Math.max(...bucketCounts.map((b) => b.count), 1);

  return (
    <div className="histogram-card">
      <div className="histogram-header">
        <h3>
          <span style={{ marginRight: 8 }}>📈</span>
          Trust Score Distribution
        </h3>
        <span className="histogram-total">{scored.length} scored</span>
      </div>

      <div className="histogram-chart">
        {bucketCounts.map((bucket, idx) => {
          const heightPct = (bucket.count / maxCount) * 100;
          return (
            <div key={bucket.label} className="histogram-column">
              <div className="histogram-bar-wrapper">
                <span className="histogram-bar-count">
                  {bucket.count > 0 ? bucket.count : ""}
                </span>
                <div
                  className="histogram-bar"
                  style={{
                    height: animated ? `${Math.max(heightPct, bucket.count > 0 ? 8 : 2)}%` : "2%",
                    backgroundColor: bucket.color,
                    boxShadow: bucket.count > 0 ? `0 0 12px ${bucket.color}44` : "none",
                    transitionDelay: `${idx * 0.1}s`,
                  }}
                />
              </div>
              <div className="histogram-label">{bucket.label}</div>
              <div
                className="histogram-tag"
                style={{ color: bucket.color }}
              >
                {bucket.tag}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
