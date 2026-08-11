"use client";

import { useEffect, useRef, useState } from "react";

interface TrustGaugeProps {
  score: number;
  size?: number;
  label?: string;
}

export default function TrustGauge({
  score,
  size = 200,
  label = "Trust Score",
}: TrustGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const getColor = (s: number) => {
    if (s >= 80) return "#10b981";
    if (s >= 60) return "#f59e0b";
    if (s >= 40) return "#f97316";
    return "#ef4444";
  };

  const getRiskLabel = (s: number) => {
    if (s >= 80) return "LOW RISK";
    if (s >= 60) return "MEDIUM RISK";
    if (s >= 40) return "HIGH RISK";
    return "CRITICAL";
  };

  useEffect(() => {
    const duration = 1500;
    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(score * eased));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [score]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const cx = size / 2;
    const cy = size / 2;
    const radius = size / 2 - 16;
    const lineWidth = 14;

    // Clear
    ctx.clearRect(0, 0, size, size);

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0.75 * Math.PI, 2.25 * Math.PI);
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = lineWidth;
    ctx.lineCap = "round";
    ctx.stroke();

    // Score arc
    const scoreAngle =
      0.75 * Math.PI + (animatedScore / 100) * 1.5 * Math.PI;
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    const color = getColor(animatedScore);
    gradient.addColorStop(0, color);
    gradient.addColorStop(1, color + "99");

    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0.75 * Math.PI, scoreAngle);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = "round";
    ctx.stroke();

    // Glow effect
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0.75 * Math.PI, scoreAngle);
    ctx.strokeStyle = color + "33";
    ctx.lineWidth = lineWidth + 8;
    ctx.lineCap = "round";
    ctx.stroke();
  }, [animatedScore, size]);

  const color = getColor(animatedScore);

  return (
    <div className="trust-gauge" style={{ textAlign: "center" }}>
      <div style={{ position: "relative", width: size, height: size, margin: "0 auto" }}>
        <canvas
          ref={canvasRef}
          style={{ width: size, height: size }}
        />
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: size * 0.22,
              fontWeight: 800,
              color,
              lineHeight: 1,
            }}
          >
            {animatedScore}
          </div>
          <div
            style={{
              fontSize: size * 0.07,
              color: "rgba(255,255,255,0.5)",
              marginTop: 4,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            {label}
          </div>
        </div>
      </div>
      <div
        style={{
          display: "inline-block",
          padding: "6px 20px",
          borderRadius: 20,
          background: color + "22",
          color,
          fontSize: 13,
          fontWeight: 700,
          letterSpacing: "0.1em",
          marginTop: -20,
        }}
      >
        {getRiskLabel(animatedScore)}
      </div>
    </div>
  );
}
