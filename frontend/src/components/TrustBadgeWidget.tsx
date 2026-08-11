"use client";

import { useState } from "react";

interface TrustBadgeWidgetProps {
  score: number;
  riskLevel: string;
  investigationId: string;
}

export default function TrustBadgeWidget({
  score,
  riskLevel,
  investigationId,
}: TrustBadgeWidgetProps) {
  const [copied, setCopied] = useState(false);

  const getBadgeColor = (s: number) => {
    if (s >= 80) return "#10b981";
    if (s >= 60) return "#f59e0b";
    if (s >= 40) return "#f97316";
    return "#ef4444";
  };

  const badgeColor = getBadgeColor(score);
  const snippet = `<a href="http://localhost:3000/investigate/${investigationId}" target="_blank" rel="noopener"><img src="https://img.shields.io/badge/MarketTrust%20AI-${Math.round(score)}%2F100%20(${riskLevel.toUpperCase()})-${badgeColor.replace("#", "")}?style=for-the-badge&logo=shield" alt="Verified by MarketTrust AI" /></a>`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        padding: 16,
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)" }}>
          🛡️ Embeddable Trust Seal
        </span>
        <button
          onClick={copyToClipboard}
          className="btn btn-secondary"
          style={{ padding: "4px 10px", fontSize: 11 }}
        >
          {copied ? "✓ Copied!" : "📋 Copy Snippet"}
        </button>
      </div>

      {/* Visual Badge Preview */}
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 14px",
          background: "var(--bg-card)",
          border: `1px solid ${badgeColor}66`,
          borderRadius: 20,
          marginBottom: 10,
        }}
      >
        <span style={{ fontSize: 14 }}>🛡️</span>
        <span style={{ fontSize: 11, fontWeight: 800, color: "var(--text-primary)" }}>
          VERIFIED BY MARKETTRUST AI
        </span>
        <span
          style={{
            fontSize: 12,
            fontWeight: 800,
            color: badgeColor,
            background: badgeColor + "22",
            padding: "2px 8px",
            borderRadius: 10,
          }}
        >
          {Math.round(score)} / 100
        </span>
      </div>

      <p style={{ fontSize: 11, color: "var(--text-muted)", margin: 0 }}>
        Embed this seal on website pages or social posts to demonstrate audit transparency.
      </p>
    </div>
  );
}
