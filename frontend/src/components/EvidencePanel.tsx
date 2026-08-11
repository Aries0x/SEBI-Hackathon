"use client";

import { useState } from "react";
import { Evidence } from "@/lib/api";

interface EvidencePanelProps {
  evidence: Evidence[];
}

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  if (!evidence || evidence.length === 0) {
    return (
      <div className="evidence-empty">
        <p>No evidence gathered yet.</p>
      </div>
    );
  }

  const toggle = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const sourceIcons: Record<string, string> = {
    chromadb: "🔍",
    llm_reasoning: "🤖",
    heuristic: "📏",
    red_flag_detection: "🚩",
    sebi_db: "🏛️",
    url_check: "🔗",
    unverified: "❓",
  };

  return (
    <div className="evidence-panel">
      {evidence.map((ev) => {
        const isExpanded = expandedIds.has(ev.id);
        const icon = sourceIcons[ev.source] || "📋";

        return (
          <div
            key={ev.id}
            className={`evidence-card ${ev.supports ? "supports" : "contradicts"}`}
            onClick={() => toggle(ev.id)}
            role="button"
            tabIndex={0}
          >
            <div className="evidence-header">
              <div className="evidence-left">
                <span className="evidence-icon">{icon}</span>
                <span className="evidence-source">{ev.source.replace(/_/g, " ")}</span>
                <span
                  className={`evidence-verdict ${ev.supports ? "supports" : "contradicts"}`}
                >
                  {ev.supports ? "Supports" : "Contradicts"}
                </span>
              </div>
              <div className="evidence-right">
                <span className="evidence-confidence">
                  {Math.round(ev.confidence * 100)}% confident
                </span>
                <span className={`evidence-chevron ${isExpanded ? "expanded" : ""}`}>
                  ▼
                </span>
              </div>
            </div>

            {isExpanded && (
              <div className="evidence-body">
                <p className="evidence-explanation">{ev.explanation}</p>
                {ev.source_url && (
                  <a
                    href={ev.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="evidence-link"
                    onClick={(e) => e.stopPropagation()}
                  >
                    View Source →
                  </a>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
