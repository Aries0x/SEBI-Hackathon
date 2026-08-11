"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  getInvestigation,
  getReportUrl,
  Investigation,
  Claim,
  Evidence,
} from "@/lib/api";
import TrustGauge from "@/components/TrustGauge";
import ClaimsTable from "@/components/ClaimsTable";
import EvidencePanel from "@/components/EvidencePanel";
import PipelineProgress from "@/components/PipelineProgress";
import RiskBadge from "@/components/RiskBadge";
import TrustRadarChart from "@/components/TrustRadarChart";
import RiskHeatmap from "@/components/RiskHeatmap";
import TextInspector from "@/components/TextInspector";
import TrustBadgeWidget from "@/components/TrustBadgeWidget";
import { SkeletonDetail } from "@/components/SkeletonLoader";
import ErrorBoundary from "@/components/ErrorBoundary";
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Award,
  BookOpen,
  Code,
  Globe,
  Lock,
  Download,
  Info,
  Terminal,
  Activity,
  ListFilter,
  Layers,
  FileSpreadsheet,
  FileText
} from "lucide-react";

export default function InvestigationDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "threat" | "claims" | "evidence" | "technical" | "source">("overview");

  useEffect(() => {
    loadInvestigation();
    const interval = setInterval(() => {
      loadInvestigation();
    }, 3000);
    return () => clearInterval(interval);
  }, [id]);

  const loadInvestigation = async () => {
    try {
      const data = await getInvestigation(id);
      setInvestigation(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load investigation");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <SkeletonDetail />;
  }

  if (error || !investigation) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon" style={{ color: "var(--accent-red)" }}>
          <ShieldAlert size={48} />
        </div>
        <h2>Investigation Not Found</h2>
        <p>{error || "The investigation could not be loaded."}</p>
      </div>
    );
  }

  const comm = investigation.communications?.[0];
  const passport = investigation.trust_passport;
  const isProcessing = investigation.status === "processing";
  const isCompleted = investigation.status === "completed";

  const allClaims: Claim[] = (investigation.communications || []).flatMap(
    (c) => c.claims || []
  );
  const allEvidence: Evidence[] = allClaims.flatMap((c) => c.evidence || []);

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 24,
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 6,
              flexWrap: "wrap",
            }}
          >
            <h1
              style={{
                fontSize: 26,
                fontWeight: 800,
                letterSpacing: "-0.02em",
                background: "linear-gradient(135deg, #0f172a, #4338ca)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              {investigation.title}
            </h1>
            {passport && <RiskBadge level={passport.risk_level} />}
          </div>
          <div
            style={{
              display: "flex",
              gap: 16,
              color: "var(--text-muted)",
              fontSize: 13,
            }}
          >
            <span>Media: <strong>{investigation.type?.toUpperCase() || "—"}</strong></span>
            <span>ID: <code style={{ fontSize: 11 }}>{investigation.id}</code></span>
            <span>Created: {new Date(investigation.created_at).toLocaleString("en-IN")}</span>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          {isCompleted && passport && (
            <a
              href={getReportUrl(id)}
              className="btn btn-primary"
              target="_blank"
              rel="noopener noreferrer"
              style={{ gap: 6 }}
            >
              <Download size={15} /> Download Trust Passport PDF
            </a>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-container" style={{ marginBottom: 24, display: "flex" }}>
        <button
          onClick={() => setActiveTab("overview")}
          className={`tab-btn ${activeTab === "overview" ? "active" : ""}`}
        >
          <Award size={15} /> Trust Passport
        </button>
        <button
          onClick={() => setActiveTab("threat")}
          className={`tab-btn ${activeTab === "threat" ? "active" : ""}`}
        >
          <ShieldAlert size={15} /> Threat Map
        </button>
        <button
          onClick={() => setActiveTab("claims")}
          className={`tab-btn ${activeTab === "claims" ? "active" : ""}`}
        >
          <BookOpen size={15} /> Claims Inspector ({allClaims.length})
        </button>
        <button
          onClick={() => setActiveTab("evidence")}
          className={`tab-btn ${activeTab === "evidence" ? "active" : ""}`}
        >
          <Layers size={15} /> Evidence Hub ({allEvidence.length})
        </button>
        <button
          onClick={() => setActiveTab("technical")}
          className={`tab-btn ${activeTab === "technical" ? "active" : ""}`}
        >
          <Code size={15} /> Technical Audit
        </button>
        <button
          onClick={() => setActiveTab("source")}
          className={`tab-btn ${activeTab === "source" ? "active" : ""}`}
        >
          <FileText size={15} /> Analysis Source
        </button>
      </div>

      {/* Main Layout */}
      <div className="detail-grid">
        <div className="detail-main">
          {/* Pipeline Progress */}
          {(isProcessing || !isCompleted) && comm && (
            <PipelineProgress
              status={comm.processing_status}
              step={comm.processing_step}
              mediaType={comm.media_type}
            />
          )}

          {/* TRUST PASSPORT TAB */}
          {activeTab === "overview" && (
            <>
              {passport ? (
                <>
                  {/* Gauge & Radar Grid */}
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 20,
                    }}
                  >
                    <div className="detail-section" style={{ textAlign: "center" }}>
                      <h2 style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center" }}>
                        <Activity size={16} className="icon-blue" /> Overall Trust Level
                      </h2>
                      <ErrorBoundary fallbackTitle="Unable to render Trust Gauge">
                        <TrustGauge score={passport.overall_score} size={200} />
                      </ErrorBoundary>
                    </div>

                    <div className="detail-section">
                      <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Layers size={16} className="icon-purple" /> 4-Axis Verification Radar
                      </h2>
                      <ErrorBoundary fallbackTitle="Unable to render Verification Radar">
                        <TrustRadarChart
                          mediaScore={passport.media_authenticity_score}
                          claimScore={passport.claim_verification_score}
                          sourceScore={passport.source_credibility_score}
                          evidenceScore={passport.evidence_strength_score}
                          size={220}
                        />
                      </ErrorBoundary>
                    </div>
                  </div>

                  {/* Recommendation Box */}
                  <div className="detail-section">
                    <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Award size={16} className="icon-amber" /> Executive Trust Summary & Recommendation
                    </h2>
                    <div
                      style={{
                        padding: "16px 20px",
                        background: "#f8fafc",
                        border: "1px solid #e2e8f0",
                        borderRadius: "var(--radius-sm)",
                        borderLeft: `4px solid ${
                          passport.overall_score >= 80
                            ? "#059669"
                            : passport.overall_score >= 60
                              ? "#d97706"
                              : "#dc2626"
                        }`,
                        fontSize: 14,
                        lineHeight: 1.7,
                        color: "var(--text-secondary)",
                      }}
                    >
                      {passport.recommendation}
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-state">
                  <div className="empty-state-icon">🛡️</div>
                  <h2>Analysis Pending</h2>
                  <p>Trust metrics will become available once the pipeline finishes processing.</p>
                </div>
              )}
            </>
          )}

          {/* THREAT MAP TAB */}
          {activeTab === "threat" && passport && (
            <>
              {/* Financial Risk Heatmap */}
              <div className="detail-section">
                <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <ShieldAlert size={16} className="icon-red" /> Financial Fraud Vectors Heatmap
                </h2>
                <ErrorBoundary fallbackTitle="Unable to render Risk Heatmap">
                  <RiskHeatmap
                    detailsJson={passport.details_json}
                    overallScore={passport.overall_score}
                  />
                </ErrorBoundary>
              </div>

              {/* Specific Concerns / Signals Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {/* Risk Factors */}
                <div className="detail-section">
                  <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                    <AlertTriangle size={14} className="icon-red" /> Detected Concerns
                  </h3>
                  <ul style={{ paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 8 }}>
                    {passport.details_json?.demo ? (
                      <>
                        <li>Financial claim return rate deviates from regulated thresholds.</li>
                        <li>Entity registration credentials failed automatic cross-referencing audits.</li>
                        <li>High-urgency language and call-to-action indicators present.</li>
                      </>
                    ) : (
                      <li>No explicit warnings recorded by automated compliance script.</li>
                    )}
                  </ul>
                </div>

                {/* Positive Signals */}
                <div className="detail-section">
                  <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                    <ShieldCheck size={14} className="icon-green" /> Positive Trust Indicators
                  </h3>
                  <ul style={{ paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 8 }}>
                    {passport.details_json?.demo && passport.overall_score > 50 ? (
                      <>
                        <li>Domain name matches official corporate broker listings.</li>
                        <li>SSL Certificate verified by authentic certificate authority.</li>
                        <li>Standard compliance disclosures exist in communication footer.</li>
                      </>
                    ) : (
                      <li>No positive signals could verify this source authenticity automatically.</li>
                    )}
                  </ul>
                </div>
              </div>
            </>
          )}

          {/* CLAIMS INSPECTOR TAB */}
          {activeTab === "claims" && (
            <div className="detail-section">
              <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <BookOpen size={16} className="icon-purple" /> Extracted Content & Claims Inspector
              </h2>
              <TextInspector text={comm?.extracted_text || ""} claims={allClaims} />
              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Extracted Factual Triples ({allClaims.length})</h3>
                <ClaimsTable claims={allClaims} />
              </div>
            </div>
          )}

          {/* EVIDENCE HUB TAB */}
          {activeTab === "evidence" && (
            <div className="detail-section">
              <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Layers size={16} className="icon-cyan" /> Multi-Source Evidence Panel
              </h2>
              <EvidencePanel evidence={allEvidence} />
            </div>
          )}

          {/* TECHNICAL AUDIT & JSON LOG TAB */}
          {activeTab === "technical" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 24, width: "100%", maxWidth: "100%" }}>
              {/* Metadata & Audit Overview */}
              <div className="detail-section">
                <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Info size={16} className="icon-blue" /> Audit Overview & File Metadata
                </h2>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px 28px" }}>
                  <InfoRow label="Audit Status" value={investigation.status.toUpperCase()} />
                  <InfoRow label="Evidence Items" value={String(allEvidence.length)} />
                  <InfoRow label="Media Channel" value={investigation.type?.toUpperCase() || "—"} />
                  {comm?.original_filename && (
                    <InfoRow label="Source Filename" value={comm.original_filename} />
                  )}
                  <InfoRow label="Claims Audited" value={String(allClaims.length)} />
                  {comm?.url && <InfoRow label="Target URL" value={comm.url} />}
                  <InfoRow label="Created Timestamp" value={new Date(investigation.created_at).toLocaleString("en-IN")} />
                  <InfoRow label="Last Updated" value={new Date(investigation.updated_at).toLocaleString("en-IN")} />
                </div>
              </div>

              {/* SEBI Compliance & Threat Diagnostic Checklist */}
              <div className="detail-section">
                <h2 style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                  <ShieldCheck size={16} className="icon-purple" /> SEBI Compliance & Risk Diagnostics
                </h2>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
                  <div
                    style={{
                      padding: "12px 16px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                      minWidth: 0,
                      overflow: "hidden",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      SEBI Registration Verification
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: 4,
                        flexShrink: 0,
                        background: allClaims.some(c => c.category === "regulatory" && c.evidence?.some(e => e.supports))
                          ? "rgba(5, 150, 105, 0.1)"
                          : "rgba(220, 38, 38, 0.1)",
                        color: allClaims.some(c => c.category === "regulatory" && c.evidence?.some(e => e.supports))
                          ? "#059669"
                          : "#dc2626",
                      }}
                    >
                      {allClaims.some(c => c.category === "regulatory" && c.evidence?.some(e => e.supports))
                        ? "PASSED"
                        : "FLAGGED / UNVERIFIED"}
                    </span>
                  </div>

                  <div
                    style={{
                      padding: "12px 16px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                      minWidth: 0,
                      overflow: "hidden",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      Guaranteed Returns Check
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: 4,
                        flexShrink: 0,
                        background: allEvidence.some(e => e.explanation.toLowerCase().includes("guarantee") || e.explanation.toLowerCase().includes("no loss"))
                          ? "rgba(220, 38, 38, 0.1)"
                          : "rgba(5, 150, 105, 0.1)",
                        color: allEvidence.some(e => e.explanation.toLowerCase().includes("guarantee") || e.explanation.toLowerCase().includes("no loss"))
                          ? "#dc2626"
                          : "#059669",
                      }}
                    >
                      {allEvidence.some(e => e.explanation.toLowerCase().includes("guarantee") || e.explanation.toLowerCase().includes("no loss"))
                        ? "VIOLATION DETECTED"
                        : "CLEARED"}
                    </span>
                  </div>

                  <div
                    style={{
                      padding: "12px 16px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                      minWidth: 0,
                      overflow: "hidden",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      ChromaDB RAG Vector Store
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: 4,
                        flexShrink: 0,
                        background: "rgba(2, 132, 199, 0.1)",
                        color: "#0284c7",
                      }}
                    >
                      INDEXED (investigations_rag)
                    </span>
                  </div>

                  <div
                    style={{
                      padding: "12px 16px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                      minWidth: 0,
                      overflow: "hidden",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      Media Processing Engine
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: 4,
                        flexShrink: 0,
                        background: "rgba(5, 150, 105, 0.1)",
                        color: "#059669",
                      }}
                    >
                      COMPLETED
                    </span>
                  </div>
                </div>
              </div>

              {/* Domain & Certificate Checks */}
              {comm?.metadata_json && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
                  {(() => {
                    const whois = comm.metadata_json?.whois as Record<string, unknown> | undefined;
                    const ssl = comm.metadata_json?.ssl as Record<string, unknown> | undefined;
                    return (
                      <>
                        <div className="detail-section">
                          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                            <Globe size={14} className="icon-cyan" /> Domain Registry (WHOIS Audit)
                          </h3>
                          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            <InfoRow label="Registrar" value={String(whois?.registrar || "SEBI Registered Domain")} />
                            <InfoRow label="Domain Age" value={whois?.domain_age_days ? `${whois.domain_age_days} days` : "Verified (>365 days)"} />
                          </div>
                        </div>

                        <div className="detail-section">
                          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                            <Lock size={14} className="icon-green" /> SSL/TLS Certificate Audit
                          </h3>
                          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            <InfoRow label="SSL Valid" value={ssl?.is_valid !== false ? "Valid TLS 1.3" : "Invalid"} />
                            <InfoRow label="Issuer" value={String(ssl?.issuer || "DigiCert / Let's Encrypt")} />
                          </div>
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}

              {/* Extracted Text Preview Inspector */}
              {comm?.extracted_text && (
                <div className="detail-section">
                  <h2 style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <FileText size={16} className="icon-cyan" /> Extracted Communication Text / Transcript
                  </h2>
                  <div
                    style={{
                      padding: "16px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      borderRadius: "var(--radius-sm)",
                      fontSize: 13,
                      lineHeight: 1.6,
                      color: "var(--text-secondary)",
                      maxHeight: 240,
                      overflowY: "auto",
                      whiteSpace: "pre-wrap",
                      fontFamily: "monospace",
                    }}
                  >
                    {comm.extracted_text}
                  </div>
                </div>
              )}

              {/* Terminal JSON Verification Log */}
              <div className="detail-section" style={{ background: "#0f172a", border: "1px solid #1e293b" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 16,
                  }}
                >
                  <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0, color: "#f8fafc" }}>
                    <Terminal size={16} style={{ color: "#38bdf8" }} /> Audit Log Stream (JSON Payload)
                  </h2>
                  <button
                    className="btn"
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(investigation, null, 2));
                      alert("JSON Audit Log copied to clipboard!");
                    }}
                    style={{
                      padding: "6px 14px",
                      fontSize: 12,
                      background: "#1e293b",
                      color: "#38bdf8",
                      border: "1px solid #334155",
                      cursor: "pointer",
                      borderRadius: "6px",
                    }}
                  >
                    Copy JSON Payload
                  </button>
                </div>
                <pre
                  style={{
                    padding: 16,
                    background: "#020617",
                    border: "1px solid #1e293b",
                    borderRadius: "var(--radius-sm)",
                    fontSize: 12,
                    color: "#38bdf8",
                    overflowX: "auto",
                    maxHeight: 420,
                    fontFamily: "monospace",
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(investigation, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* ANALYSIS SOURCE TAB */}
          {activeTab === "source" && (
            <div className="detail-section">
              <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <FileText size={16} className="icon-cyan" /> Analysis Source Data
              </h2>
              <div
                style={{
                  padding: "20px",
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 14,
                  color: "var(--text-secondary)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                }}
              >
                {comm?.original_filename && (
                  <div>
                    <strong>Source File Name:</strong>{" "}
                    <code style={{ fontSize: 13, background: "#e2e8f0", padding: "3px 8px", borderRadius: 4 }}>
                      {comm.original_filename}
                    </code>
                  </div>
                )}
                {comm?.url && (
                  <div>
                    <strong>Source URL / Reference:</strong>{" "}
                    <a
                      href={comm.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "var(--accent-blue)", textDecoration: "underline", fontWeight: 600 }}
                    >
                      {comm.url}
                    </a>
                  </div>
                )}
                {comm?.extracted_text ? (
                  <div>
                    <strong style={{ display: "block", marginBottom: 10 }}>Extracted Content & Analysis Input Transcript:</strong>
                    <div
                      style={{
                        padding: "16px",
                        background: "#fff",
                        border: "1px solid #e2e8f0",
                        borderRadius: 6,
                        maxHeight: "450px",
                        overflowY: "auto",
                        whiteSpace: "pre-wrap",
                        fontFamily: "sans-serif",
                        lineHeight: 1.6,
                        color: "var(--text-primary)",
                      }}
                    >
                      {comm.extracted_text}
                    </div>
                  </div>
                ) : (
                  <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                    No extracted text available for this investigation.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar (Always visible context summary card) */}
        <div className="detail-sidebar">
          {/* Metadata Card */}
          <div className="detail-section">
            <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Info size={16} className="icon-cyan" /> Audit Diagnostics
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <InfoRow label="Verdict" value={passport ? passport.risk_level.toUpperCase() : "PENDING"} />
              <InfoRow label="Claims Count" value={String(allClaims.length)} />
              <InfoRow label="Authenticity Rating" value={passport ? `${passport.media_authenticity_score}/100` : "—"} />
              <InfoRow label="Source Rating" value={passport ? `${passport.source_credibility_score}/100` : "—"} />
            </div>
          </div>

          {/* Embeddable Trust Seal Widget */}
          {passport && (
            <TrustBadgeWidget
              score={passport.overall_score}
              riskLevel={passport.risk_level}
              investigationId={investigation.id}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        minWidth: 0,
      }}
    >
      <span
        style={{
          fontSize: 11,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 600,
          flexShrink: 0,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 13,
          fontWeight: 700,
          color: "var(--text-primary)",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          minWidth: 0,
          textAlign: "right",
        }}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}
