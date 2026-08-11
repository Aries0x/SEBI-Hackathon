"use client";

interface RiskHeatmapProps {
  detailsJson?: Record<string, unknown> | null;
  overallScore: number;
}

export default function RiskHeatmap({
  detailsJson,
  overallScore,
}: RiskHeatmapProps) {
  // 6 Financial Fraud Risk Vectors
  const vectors = [
    {
      key: "guaranteed_return",
      name: "Guaranteed Return Claims",
      desc: "Promises of fixed/assured return percentages",
      severity: overallScore < 50 ? "high" : "low",
    },
    {
      key: "sebi_registration",
      name: "Regulatory Credentials",
      desc: "Verification of SEBI broker/adviser reg numbers",
      severity: overallScore < 60 ? "high" : "low",
    },
    {
      key: "media_tampering",
      name: "Media Integrity (ELA)",
      desc: "Digital photo manipulation & pixel tampering",
      severity: overallScore < 40 ? "critical" : overallScore < 70 ? "medium" : "low",
    },
    {
      key: "domain_age",
      name: "Domain Infrastructure",
      desc: "WHOIS age, SSL validity, and DNS records",
      severity: overallScore < 50 ? "medium" : "low",
    },
    {
      key: "urgency_tactics",
      name: "Urgency Pressure",
      desc: "Limited-time pressure & aggressive calls-to-action",
      severity: overallScore < 55 ? "medium" : "low",
    },
    {
      key: "unauthorized_channel",
      name: "Informal Channels",
      desc: "WhatsApp/Telegram private group tip provisions",
      severity: overallScore < 45 ? "high" : "low",
    },
  ];

  const severityConfig: Record<string, { label: string; bg: string; color: string; icon: string }> = {
    low: { label: "Pass", bg: "rgba(16, 185, 129, 0.12)", color: "#10b981", icon: "✓" },
    medium: { label: "Caution", bg: "rgba(245, 158, 11, 0.12)", color: "#f59e0b", icon: "⚡" },
    high: { label: "Warning", bg: "rgba(249, 115, 22, 0.12)", color: "#f97316", icon: "⚠️" },
    critical: { label: "Critical Flag", bg: "rgba(239, 68, 68, 0.15)", color: "#ef4444", icon: "🚨" },
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
      {vectors.map((vec) => {
        const conf = severityConfig[vec.severity] || severityConfig.low;
        return (
          <div
            key={vec.key}
            style={{
              padding: "12px 14px",
              background: "var(--bg-surface)",
              border: `1px solid ${conf.color}33`,
              borderRadius: "var(--radius-sm)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                {vec.name}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                {vec.desc}
              </div>
            </div>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                padding: "2px 8px",
                borderRadius: 12,
                fontSize: 11,
                fontWeight: 700,
                color: conf.color,
                background: conf.bg,
                whiteSpace: "nowrap",
              }}
            >
              <span>{conf.icon}</span>
              <span>{conf.label}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
