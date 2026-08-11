"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { InvestigationSummary } from "@/lib/api";
import Link from "next/link";
import { ExternalLink, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

interface NetworkNode {
  id: string;
  label: string;
  count: number;
  riskLevel: string;
  investigations: { id: string; title: string; score: number | null; risk: string | null }[];
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
}

interface FraudNetworkGraphProps {
  investigations: InvestigationSummary[];
}

const RISK_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#059669",
  unknown: "#64748b",
};

const RISK_GLOW: Record<string, string> = {
  critical: "rgba(220, 38, 38, 0.4)",
  high: "rgba(234, 88, 12, 0.35)",
  medium: "rgba(217, 119, 6, 0.3)",
  low: "rgba(5, 150, 105, 0.3)",
  unknown: "rgba(100, 116, 139, 0.2)",
};

function buildGraph(investigations: InvestigationSummary[]) {
  const entityMap = new Map<string, NetworkNode>();
  const edgeMap = new Map<string, NetworkEdge>();

  // Extract entities from investigation titles using keyword extraction
  investigations.forEach((inv) => {
    const title = inv.title || "";
    // Extract key entity names from titles
    const entities: string[] = [];

    // Known entity patterns from demo scenarios and real investigations
    const patterns = [
      /(?:SEBI|sebi)/i,
      /(?:Zerodha|ICICI|HDFC|Kotak|Angel|Upstox|Groww)/i,
      /(?:Deepfake|Phishing|Forgery|Spoofed|Photoshopped)/i,
      /(?:WhatsApp|Telegram|YouTube|Instagram)/i,
      /(?:IPO|P&L|Stock|Nifty|Sensex)/i,
      /(?:Broker|Advisory|Investment|Trading)/i,
    ];

    // Group into meaningful entity labels
    if (/deepfake|video/i.test(title)) entities.push("Deepfake Video");
    if (/photoshopped|P&L|forgery|image/i.test(title)) entities.push("Image Forgery");
    if (/phishing|spoofed|email/i.test(title)) entities.push("Email Phishing");
    if (/broker|legitimate|ICICI|research/i.test(title)) entities.push("Broker Note");
    if (/SEBI/i.test(title)) entities.push("SEBI Regulatory");
    if (/IPO/i.test(title)) entities.push("IPO Scam");
    if (/YouTube|Telegram|WhatsApp/i.test(title)) entities.push("Social Media");
    if (/guaranteed|return|profit|risk.free/i.test(title)) entities.push("Guaranteed Returns");
    if (/Zerodha/i.test(title)) entities.push("Zerodha Platform");
    if (/website|audit/i.test(title)) entities.push("Website Audit");

    // Fallback: use media type
    if (entities.length === 0) {
      entities.push(inv.type?.toUpperCase() || "Unknown");
    }

    // Register entities
    entities.forEach((entity) => {
      if (!entityMap.has(entity)) {
        entityMap.set(entity, {
          id: entity,
          label: entity,
          count: 0,
          riskLevel: "unknown",
          investigations: [],
          x: Math.random() * 600 + 100,
          y: Math.random() * 400 + 100,
          vx: 0,
          vy: 0,
          radius: 20,
        });
      }
      const node = entityMap.get(entity)!;
      node.count++;
      node.investigations.push({
        id: inv.id,
        title: inv.title,
        score: inv.trust_score,
        risk: inv.risk_level,
      });

      // Set risk level to highest found
      const riskOrder = ["critical", "high", "medium", "low"];
      const invRisk = inv.risk_level || "unknown";
      if (riskOrder.indexOf(invRisk) < riskOrder.indexOf(node.riskLevel) || node.riskLevel === "unknown") {
        node.riskLevel = invRisk;
      }
    });

    // Create edges between co-occurring entities
    for (let i = 0; i < entities.length; i++) {
      for (let j = i + 1; j < entities.length; j++) {
        const key = [entities[i], entities[j]].sort().join("|||");
        if (!edgeMap.has(key)) {
          edgeMap.set(key, { source: entities[i], target: entities[j], weight: 0 });
        }
        edgeMap.get(key)!.weight++;
      }
    }
  });

  // Calculate node radii
  const maxCount = Math.max(...Array.from(entityMap.values()).map((n) => n.count), 1);
  entityMap.forEach((node) => {
    node.radius = 18 + (node.count / maxCount) * 28;
  });

  return {
    nodes: Array.from(entityMap.values()),
    edges: Array.from(edgeMap.values()),
  };
}

export default function FraudNetworkGraph({ investigations }: FraudNetworkGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [edges, setEdges] = useState<NetworkEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const animationRef = useRef<number | null>(null);
  const iterRef = useRef(0);

  useEffect(() => {
    const { nodes: n, edges: e } = buildGraph(investigations);
    setNodes(n);
    setEdges(e);
  }, [investigations]);

  // Force-directed simulation
  useEffect(() => {
    if (nodes.length === 0) return;

    iterRef.current = 0;
    const maxIter = 200;
    const cx = dimensions.width / 2;
    const cy = dimensions.height / 2;

    const simulate = () => {
      iterRef.current++;
      const alpha = Math.max(0.01, 1 - iterRef.current / maxIter);

      setNodes((prev) => {
        const next = prev.map((n) => ({ ...n }));

        // Repulsion between nodes
        for (let i = 0; i < next.length; i++) {
          for (let j = i + 1; j < next.length; j++) {
            const dx = next[j].x - next[i].x;
            const dy = next[j].y - next[i].y;
            const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
            const force = (800 * alpha) / (dist * dist);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            next[i].vx -= fx;
            next[i].vy -= fy;
            next[j].vx += fx;
            next[j].vy += fy;
          }
        }

        // Edge attraction
        edges.forEach((edge) => {
          const si = next.findIndex((n) => n.id === edge.source);
          const ti = next.findIndex((n) => n.id === edge.target);
          if (si === -1 || ti === -1) return;
          const dx = next[ti].x - next[si].x;
          const dy = next[ti].y - next[si].y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = (dist - 120) * 0.02 * alpha;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          next[si].vx += fx;
          next[si].vy += fy;
          next[ti].vx -= fx;
          next[ti].vy -= fy;
        });

        // Center gravity
        next.forEach((n) => {
          n.vx += (cx - n.x) * 0.005 * alpha;
          n.vy += (cy - n.y) * 0.005 * alpha;
        });

        // Apply velocity with damping
        next.forEach((n) => {
          n.vx *= 0.85;
          n.vy *= 0.85;
          n.x += n.vx;
          n.y += n.vy;
          // Keep in bounds
          n.x = Math.max(n.radius + 10, Math.min(dimensions.width - n.radius - 10, n.x));
          n.y = Math.max(n.radius + 10, Math.min(dimensions.height - n.radius - 10, n.y));
        });

        return next;
      });

      if (iterRef.current < maxIter) {
        animationRef.current = requestAnimationFrame(simulate);
      }
    };

    animationRef.current = requestAnimationFrame(simulate);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [nodes.length, edges, dimensions]);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 2.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.4));
  const handleReset = () => { setZoom(1); setSelectedNode(null); };

  const getNodePos = useCallback(
    (id: string) => {
      const node = nodes.find((n) => n.id === id);
      return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
    },
    [nodes]
  );

  if (investigations.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🕸️</div>
        <h2>No Network Data</h2>
        <p>Add investigations to visualize fraud entity connections.</p>
      </div>
    );
  }

  return (
    <div className="fraud-network-container">
      {/* Controls */}
      <div className="network-controls">
        <button onClick={handleZoomIn} className="network-control-btn" title="Zoom In">
          <ZoomIn size={16} />
        </button>
        <button onClick={handleZoomOut} className="network-control-btn" title="Zoom Out">
          <ZoomOut size={16} />
        </button>
        <button onClick={handleReset} className="network-control-btn" title="Reset View">
          <Maximize2 size={16} />
        </button>
        <span className="network-stats">
          {nodes.length} entities · {edges.length} connections
        </span>
      </div>

      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        style={{
          width: "100%",
          height: 480,
          cursor: "grab",
          transform: `scale(${zoom})`,
          transformOrigin: "center",
          transition: "transform 0.2s ease",
        }}
      >
        <defs>
          {/* Glow filters for each risk level */}
          {Object.entries(RISK_GLOW).map(([level, color]) => (
            <filter key={level} id={`glow-${level}`} x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor={color} floodOpacity="1" />
            </filter>
          ))}
          {/* Edge gradient */}
          <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0d9488" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.3" />
          </linearGradient>
        </defs>

        {/* Edges */}
        {edges.map((edge, idx) => {
          const s = getNodePos(edge.source);
          const t = getNodePos(edge.target);
          return (
            <line
              key={idx}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke="url(#edge-gradient)"
              strokeWidth={1.5 + edge.weight * 0.8}
              strokeLinecap="round"
              opacity={0.6}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const color = RISK_COLORS[node.riskLevel] || RISK_COLORS.unknown;
          const isSelected = selectedNode?.id === node.id;
          return (
            <g
              key={node.id}
              onClick={() => setSelectedNode(isSelected ? null : node)}
              style={{ cursor: "pointer" }}
            >
              {/* Outer glow ring */}
              <circle
                cx={node.x}
                cy={node.y}
                r={node.radius + 6}
                fill="none"
                stroke={color}
                strokeWidth={isSelected ? 3 : 1.5}
                strokeDasharray={isSelected ? "none" : "4 3"}
                opacity={isSelected ? 0.8 : 0.3}
                filter={`url(#glow-${node.riskLevel})`}
              />
              {/* Node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r={node.radius}
                fill={color}
                opacity={0.85}
                stroke="#ffffff"
                strokeWidth={2}
              />
              {/* Count label */}
              <text
                x={node.x}
                y={node.y + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#ffffff"
                fontSize={node.radius > 30 ? 14 : 11}
                fontWeight={700}
                style={{ pointerEvents: "none" }}
              >
                {node.count}
              </text>
              {/* Entity name */}
              <text
                x={node.x}
                y={node.y + node.radius + 14}
                textAnchor="middle"
                fill="#334155"
                fontSize={11}
                fontWeight={600}
                style={{ pointerEvents: "none" }}
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="network-legend">
        {Object.entries(RISK_COLORS)
          .filter(([k]) => k !== "unknown")
          .map(([level, color]) => (
            <span key={level} className="network-legend-item">
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: color,
                  display: "inline-block",
                  boxShadow: `0 0 6px ${color}`,
                }}
              />
              <span style={{ textTransform: "capitalize" }}>{level}</span>
            </span>
          ))}
      </div>

      {/* Selected Node Detail Card */}
      {selectedNode && (
        <div className="network-tooltip">
          <div className="network-tooltip-header">
            <span
              className="network-tooltip-dot"
              style={{ background: RISK_COLORS[selectedNode.riskLevel] }}
            />
            <span className="network-tooltip-title">{selectedNode.label}</span>
            <span className="network-tooltip-count">{selectedNode.count} case{selectedNode.count !== 1 ? "s" : ""}</span>
          </div>
          <div className="network-tooltip-list">
            {selectedNode.investigations.slice(0, 6).map((inv) => (
              <Link
                key={inv.id}
                href={`/investigate/${inv.id}`}
                className="network-tooltip-inv"
              >
                <span className="network-tooltip-inv-title">{inv.title}</span>
                <div className="network-tooltip-inv-meta">
                  {inv.score !== null && (
                    <span
                      style={{
                        fontWeight: 700,
                        color: inv.score >= 80 ? "#059669" : inv.score >= 60 ? "#d97706" : "#dc2626",
                      }}
                    >
                      {Math.round(inv.score)}/100
                    </span>
                  )}
                  {inv.risk && (
                    <span
                      style={{
                        fontSize: 9,
                        fontWeight: 700,
                        padding: "1px 6px",
                        borderRadius: 4,
                        textTransform: "uppercase",
                        color: RISK_COLORS[inv.risk] || "#64748b",
                        background: `${RISK_COLORS[inv.risk] || "#64748b"}18`,
                      }}
                    >
                      {inv.risk}
                    </span>
                  )}
                  <ExternalLink size={11} style={{ color: "#64748b" }} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
