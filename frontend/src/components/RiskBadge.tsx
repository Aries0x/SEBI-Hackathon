"use client";

import { CheckCircle2, AlertTriangle, ShieldAlert, Activity } from "lucide-react";

interface RiskBadgeProps {
  level?: string | null;
  size?: "sm" | "md" | "lg";
}

const RISK_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  low: { label: "Low Risk", color: "#10b981", bg: "rgba(16,185,129,0.12)" },
  medium: { label: "Medium Risk", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  high: { label: "High Risk", color: "#f97316", bg: "rgba(249,115,22,0.12)" },
  critical: { label: "Critical", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  unknown: { label: "Pending", color: "#6b7280", bg: "rgba(107,114,128,0.12)" },
};

const SIZE_STYLES = {
  sm: { padding: "2px 8px", fontSize: 10, iconSize: 11 },
  md: { padding: "4px 14px", fontSize: 12, iconSize: 13 },
  lg: { padding: "6px 20px", fontSize: 14, iconSize: 15 },
};

export default function RiskBadge({ level, size = "md" }: RiskBadgeProps) {
  const normalizedLevel = (level || "unknown").toLowerCase();
  const config = RISK_CONFIG[normalizedLevel] || RISK_CONFIG.unknown;
  const sizeStyle = SIZE_STYLES[size];

  const getIcon = (lvl: string, iconSize: number) => {
    switch (lvl) {
      case "low":
        return <CheckCircle2 size={iconSize} />;
      case "medium":
      case "high":
        return <AlertTriangle size={iconSize} />;
      case "critical":
        return <ShieldAlert size={iconSize} />;
      default:
        return <Activity size={iconSize} />;
    }
  };

  return (
    <span
      className="risk-badge"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: sizeStyle.padding,
        fontSize: sizeStyle.fontSize,
        fontWeight: 700,
        borderRadius: 20,
        color: config.color,
        background: config.bg,
        border: `1px solid ${config.color}33`,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
      }}
    >
      <span style={{ display: "flex", alignItems: "center" }}>
        {getIcon(normalizedLevel, sizeStyle.iconSize)}
      </span>
      <span>{config.label}</span>
    </span>
  );
}
