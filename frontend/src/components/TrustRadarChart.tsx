"use client";

interface TrustRadarChartProps {
  mediaScore: number;
  claimScore: number;
  sourceScore: number;
  evidenceScore: number;
  size?: number;
}

export default function TrustRadarChart({
  mediaScore,
  claimScore,
  sourceScore,
  evidenceScore,
  size = 280,
}: TrustRadarChartProps) {
  const center = size / 2;
  const radius = size * 0.38;

  // 4 Axes: Top (Media), Right (Claim), Bottom (Source), Left (Evidence)
  const axes = [
    { label: "Media Authenticity", value: mediaScore, angle: -Math.PI / 2 },
    { label: "Claim Verification", value: claimScore, angle: 0 },
    { label: "Source Credibility", value: sourceScore, angle: Math.PI / 2 },
    { label: "Evidence Strength", value: evidenceScore, angle: Math.PI },
  ];

  const getPoint = (val: number, angle: number) => {
    const r = (val / 100) * radius;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  const getAxisEnd = (angle: number) => {
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  };

  // Polygon points for current scores
  const scorePoints = axes
    .map((a) => {
      const p = getPoint(a.value, a.angle);
      return `${p.x},${p.y}`;
    })
    .join(" ");

  // Grid rings (25%, 50%, 75%, 100%)
  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <div style={{ textAlign: "center", position: "relative" }}>
      <svg width={size} height={size} style={{ overflow: "visible" }}>
        {/* Background Grid Rings */}
        {rings.map((ring, idx) => {
          const rRing = radius * ring;
          const points = axes
            .map((a) => {
              const x = center + rRing * Math.cos(a.angle);
              const y = center + rRing * Math.sin(a.angle);
              return `${x},${y}`;
            })
            .join(" ");

          return (
            <polygon
              key={idx}
              points={points}
              fill={idx === 3 ? "rgba(255,255,255,0.02)" : "none"}
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="1"
              strokeDasharray={idx < 3 ? "3,3" : undefined}
            />
          );
        })}

        {/* Axis Lines */}
        {axes.map((a, idx) => {
          const end = getAxisEnd(a.angle);
          return (
            <line
              key={idx}
              x1={center}
              y1={center}
              x2={end.x}
              y2={end.y}
              stroke="rgba(255, 255, 255, 0.12)"
              strokeWidth="1.5"
            />
          );
        })}

        {/* Score Polygon Fill */}
        <polygon
          points={scorePoints}
          fill="url(#radarGradient)"
          stroke="#8b5cf6"
          strokeWidth="2.5"
          style={{ filter: "drop-shadow(0 0 10px rgba(139, 92, 246, 0.4))" }}
        />

        {/* Data Points */}
        {axes.map((a, idx) => {
          const p = getPoint(a.value, a.angle);
          return (
            <g key={idx}>
              <circle
                cx={p.x}
                cy={p.y}
                r="5"
                fill="#06b6d4"
                stroke="#ffffff"
                strokeWidth="2"
              />
            </g>
          );
        })}

        {/* Gradients */}
        <defs>
          <radialGradient id="radarGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.15" />
          </radialGradient>
        </defs>
      </svg>

      {/* Axis Labels */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "8px 16px",
          marginTop: 12,
          fontSize: 12,
        }}
      >
        {axes.map((a) => (
          <div
            key={a.label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "4px 8px",
              background: "rgba(255,255,255,0.03)",
              borderRadius: 6,
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span style={{ color: "var(--text-secondary)" }}>{a.label}</span>
            <strong
              style={{
                color:
                  a.value >= 80
                    ? "#10b981"
                    : a.value >= 60
                      ? "#f59e0b"
                      : "#ef4444",
              }}
            >
              {Math.round(a.value)}
            </strong>
          </div>
        ))}
      </div>
    </div>
  );
}
