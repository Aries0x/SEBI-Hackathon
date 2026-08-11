"use client";

import { useEffect, useState } from "react";
import { listInvestigations, InvestigationSummary, deleteInvestigation } from "@/lib/api";
import InvestigationCard from "@/components/InvestigationCard";
import RiskDistributionChart from "@/components/RiskDistributionChart";
import MediaTypeBreakdown from "@/components/MediaTypeBreakdown";
import RecentActivityTimeline from "@/components/RecentActivityTimeline";
import TrustScoreHistogram from "@/components/TrustScoreHistogram";
import { SkeletonGrid } from "@/components/SkeletonLoader";
import ErrorBoundary from "@/components/ErrorBoundary";
import AuditComparisonModal from "@/components/AuditComparisonModal";
import Link from "next/link";
import FraudNetworkGraph from "@/components/FraudNetworkGraph";
import { 
  ShieldAlert, 
  Activity, 
  TrendingUp, 
  CheckCircle2, 
  AlertTriangle,
  Search, 
  Trash2, 
  Plus,
  BarChart3,
  ListFilter,
  History,
  Video,
  Image as ImageIcon,
  Mail,
  Globe,
  FileText,
  Scale,
  Network
} from "lucide-react";

export default function DashboardPage() {
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activeDashboardTab, setActiveDashboardTab] = useState<"audits" | "analytics" | "network" | "activity">("audits");
  const [showComparison, setShowComparison] = useState(false);

  useEffect(() => {
    loadInvestigations();
    const interval = setInterval(loadInvestigations, 4000);
    return () => clearInterval(interval);
  }, []);

  const loadInvestigations = async () => {
    try {
      const data = await listInvestigations();
      setInvestigations(data);
      setError(null);
    } catch (err) {
      setError("Failed to load investigations. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  // Filtered List
  const filteredInvestigations = investigations.filter((inv) => {
    const matchesSearch = inv.title
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesType = filterType === "all" || inv.type === filterType;
    return matchesSearch && matchesType;
  });

  const handleSelect = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedIds(new Set(filteredInvestigations.map((inv) => inv.id)));
  };

  const handleClearSelection = () => {
    setSelectedIds(new Set());
  };

  const handleDeleteSingle = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this investigation?")) {
      return;
    }
    try {
      await deleteInvestigation(id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      loadInvestigations();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete investigation");
    }
  };

  const handleDeleteSelected = async () => {
    if (
      !window.confirm(
        `Are you sure you want to delete the ${selectedIds.size} selected investigation(s)?`
      )
    ) {
      return;
    }
    try {
      setLoading(true);
      await Promise.all(Array.from(selectedIds).map((id) => deleteInvestigation(id)));
      setSelectedIds(new Set());
      await loadInvestigations();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete selected investigations");
    } finally {
      setLoading(false);
    }
  };

  // Stats
  const total = investigations.length;
  const completed = investigations.filter((i) => i.status === "completed").length;
  const processing = investigations.filter((i) => i.status === "processing").length;
  const criticalCount = investigations.filter(
    (i) => i.risk_level === "critical" || i.risk_level === "high"
  ).length;

  const validScores = investigations.filter((i) => i.trust_score != null);
  const avgScore =
    validScores.length > 0
      ? Math.round(
          validScores.reduce((sum: number, i: InvestigationSummary) => sum + (i.trust_score || 0), 0) /
            validScores.length
        )
      : null;

  const threatLevel = computeThreatLevel(investigations);

  return (
    <div className="main">
      {/* Hero Header */}
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
          <div>
            <h1>Financial Trust Intelligence</h1>
            <p>Verify whether financial communications (video, image, email, website) can be trusted</p>
          </div>
          <Link href="/investigate" className="btn btn-primary" style={{ padding: "12px 26px" }}>
            <Plus size={16} style={{ marginRight: 4 }} /> New Investigation
          </Link>
        </div>
      </div>

      {/* Sub-Navigation Tab Bar */}
      <div className="tab-container">
        <button
          onClick={() => setActiveDashboardTab("audits")}
          className={`tab-btn ${activeDashboardTab === "audits" ? "active" : ""}`}
        >
          <ListFilter size={15} /> Active Audits
        </button>
        <button
          onClick={() => setActiveDashboardTab("analytics")}
          className={`tab-btn ${activeDashboardTab === "analytics" ? "active" : ""}`}
        >
          <BarChart3 size={15} /> Analytics Hub
        </button>
        <button
          onClick={() => setActiveDashboardTab("network")}
          className={`tab-btn ${activeDashboardTab === "network" ? "active" : ""}`}
        >
          <Network size={15} /> Threat Network Graph
        </button>
        <button
          onClick={() => setActiveDashboardTab("activity")}
          className={`tab-btn ${activeDashboardTab === "activity" ? "active" : ""}`}
        >
          <History size={15} /> Activity Feed
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: "20px 24px",
            background: "rgba(220, 38, 38, 0.08)",
            border: "1px solid rgba(220, 38, 38, 0.25)",
            borderRadius: "var(--radius)",
            color: "#dc2626",
            marginBottom: 24,
            display: "flex",
            alignItems: "center",
            gap: 12
          }}
        >
          <ShieldAlert size={20} className="icon-red" />
          <span><strong>Connection Error:</strong> {error}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div style={{ marginTop: 24 }}>
          <SkeletonGrid count={6} />
        </div>
      )}

      {/* Audit Comparison Modal */}
      {showComparison && (
        <AuditComparisonModal
          investigations={investigations.filter((inv) => selectedIds.has(inv.id))}
          onClose={() => setShowComparison(false)}
        />
      )}

      {/* ACTIVE AUDITS TAB */}
      {!loading && activeDashboardTab === "audits" && (
        <>
          {/* Quick Actions Panel */}
          <div className="dashboard-full-row">
            <QuickActionsPanel />
          </div>

          {/* Filter & Search Toolbar */}
          {investigations.length > 0 && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 24,
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <div style={{ position: "relative", flex: 1, minWidth: 260 }}>
                <input
                  type="text"
                  placeholder="Search audits by title..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input"
                  style={{ paddingLeft: 38 }}
                />
                <Search size={16} style={{ position: "absolute", left: 14, top: 15, opacity: 0.4 }} />
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                {["all", "video", "image", "email", "website"].map((type) => (
                  <button
                    key={type}
                    onClick={() => setFilterType(type)}
                    className={`btn ${filterType === type ? "btn-primary" : "btn-secondary"}`}
                    style={{ padding: "6px 14px", fontSize: 12, textTransform: "capitalize" }}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {investigations.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">🛡️</div>
              <h2>No active investigations</h2>
              <p>
                Start your first investigation or try a pre-configured 1-click sample scenario.
              </p>
              <Link href="/investigate" className="btn btn-primary">
                <Plus size={16} style={{ marginRight: 4 }} /> New Investigation
              </Link>
            </div>
          )}

          {/* Investigations Grid */}
          {filteredInvestigations.length > 0 && (
            <>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 14,
                  flexWrap: "wrap",
                  gap: 12,
                }}
              >
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  All Audits ({filteredInvestigations.length})
                </span>

                {/* Selection Toolbar Controls */}
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  {selectedIds.size >= 2 && (
                    <button
                      onClick={() => setShowComparison(true)}
                      className="btn btn-primary"
                      style={{ padding: "6px 14px", fontSize: 12 }}
                    >
                      <Scale size={13} style={{ marginRight: 4 }} /> Compare Selected ({selectedIds.size})
                    </button>
                  )}
                  {selectedIds.size > 0 ? (
                    <>
                      <span style={{ fontSize: 13, color: "#4f46e5", fontWeight: 600 }}>
                        {selectedIds.size} selected
                      </span>
                      <button
                        onClick={handleDeleteSelected}
                        className="btn"
                        style={{
                          background: "rgba(220, 38, 38, 0.08)",
                          border: "1px solid #dc2626",
                          color: "#dc2626",
                          padding: "6px 14px",
                          fontSize: 12,
                          cursor: "pointer",
                          borderRadius: "var(--radius-sm)",
                        }}
                      >
                        <Trash2 size={13} style={{ marginRight: 4 }} /> Delete Selected
                      </button>
                      <button
                        onClick={handleClearSelection}
                        className="btn btn-secondary"
                        style={{ padding: "6px 14px", fontSize: 12 }}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={handleSelectAll}
                      className="btn btn-secondary"
                      style={{ padding: "6px 14px", fontSize: 12 }}
                    >
                      Select All
                    </button>
                  )}
                </div>
              </div>
              <div className="cards-grid">
                {filteredInvestigations.map((inv) => (
                  <InvestigationCard
                    key={inv.id}
                    investigation={inv}
                    isSelected={selectedIds.has(inv.id)}
                    onSelect={handleSelect}
                    onDelete={handleDeleteSingle}
                  />
                ))}
              </div>
            </>
          )}
        </>
      )}

      {/* ANALYTICS HUB TAB */}
      {!loading && activeDashboardTab === "analytics" && (
        <>
          {/* Threat Level Banner */}
          {investigations.length > 0 && (
            <ThreatBanner
              level={threatLevel.level}
              description={threatLevel.description}
            />
          )}

          {/* Analytics Stats Bar */}
          {investigations.length > 0 ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 16,
                marginBottom: 24,
              }}
            >
              <StatCard label="Total Analyzed" value={total} icon={<FileText size={18} />} />
              <StatCard label="Completed" value={completed} icon={<CheckCircle2 size={18} />} color="#10b981" />
              <StatCard label="Critical Threats" value={criticalCount} icon={<ShieldAlert size={18} />} color="#ef4444" />
              <StatCard
                label="Avg. Trust Score"
                value={avgScore !== null ? `${avgScore}/100` : "—"}
                icon={<TrendingUp size={18} />}
                color={
                  avgScore === null
                    ? undefined
                    : avgScore >= 80
                      ? "#10b981"
                      : avgScore >= 60
                        ? "#f59e0b"
                        : "#ef4444"
                }
              />
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <h2>No analytics data available</h2>
              <p>Add investigations to view risk distributions and ratings trends.</p>
            </div>
          )}

          {/* Risk Distribution + Trust Score Histogram (2-Column) */}
          {investigations.length > 0 && (
            <div className="dashboard-two-col">
              <ErrorBoundary fallbackTitle="Unable to render Risk Distribution Chart">
                <RiskDistributionChart investigations={investigations} />
              </ErrorBoundary>
              <ErrorBoundary fallbackTitle="Unable to render Trust Score Histogram">
                <TrustScoreHistogram investigations={investigations} />
              </ErrorBoundary>
            </div>
          )}

          {/* Media Type Breakdown */}
          {investigations.length > 0 && (
            <div className="dashboard-full-row">
              <ErrorBoundary fallbackTitle="Unable to render Media Breakdown">
                <MediaTypeBreakdown investigations={investigations} />
              </ErrorBoundary>
            </div>
          )}
        </>
      )}

      {/* THREAT NETWORK TAB */}
      {!loading && activeDashboardTab === "network" && (
        <div className="dashboard-full-row">
          <div className="detail-section" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "18px 24px 14px", borderBottom: "1px solid var(--border)", background: "var(--bg-surface)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                  <Network size={18} className="icon-teal" /> Interactive Fraud Entity Network
                </h2>
                <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "2px 0 0" }}>
                  Visual mapping of companies, entities, and scam vectors across analyzed communications. Click any node to view related cases.
                </p>
              </div>
            </div>
            <ErrorBoundary fallbackTitle="Unable to render Fraud Network Graph">
              <FraudNetworkGraph investigations={investigations} />
            </ErrorBoundary>
          </div>
        </div>
      )}

      {/* ACTIVITY TIMELINE TAB */}
      {!loading && activeDashboardTab === "activity" && (
        <div className="dashboard-full-row">
          {investigations.length > 0 ? (
            <div className="detail-section">
              <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
                <History size={16} className="icon-cyan" /> Audit Feed Timeline
              </h2>
              <ErrorBoundary fallbackTitle="Unable to render Activity Timeline">
                <RecentActivityTimeline investigations={investigations} />
              </ErrorBoundary>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📜</div>
              <h2>No activity timeline records</h2>
              <p>Audit actions will appear here once investigations are created.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Threat Level Calculation ─────────────────────────── */

function computeThreatLevel(investigations: InvestigationSummary[]) {
  const total = investigations.length;
  if (total === 0) {
    return { level: "low", description: "No investigations yet" };
  }

  const criticalCount = investigations.filter(
    (i) => i.risk_level === "critical"
  ).length;
  const highCount = investigations.filter(
    (i) => i.risk_level === "high"
  ).length;
  const dangerousCount = criticalCount + highCount;
  const ratio = dangerousCount / total;

  if (criticalCount >= 3 || ratio >= 0.6) {
    return {
      level: "critical",
      description: `${criticalCount} critical & ${highCount} high-risk communications detected out of ${total} analyzed — immediate review recommended`,
    };
  }
  if (dangerousCount >= 2 || ratio >= 0.4) {
    return {
      level: "high",
      description: `${dangerousCount} of ${total} communications flagged as high risk — exercise caution`,
    };
  }
  if (dangerousCount >= 1 || ratio >= 0.2) {
    return {
      level: "elevated",
      description: `${dangerousCount} flagged communication${dangerousCount > 1 ? "s" : ""} out of ${total} analyzed — monitoring active`,
    };
  }
  return {
    level: "low",
    description: `All ${total} analyzed communication${total > 1 ? "s" : ""} within acceptable trust thresholds`,
  };
}

/* ── Threat Banner Component ──────────────────────────── */

function ThreatBanner({
  level,
  description,
}: {
  level: string;
  description: string;
}) {
  const config: Record<string, { icon: React.ReactNode; label: string }> = {
    low: { icon: <CheckCircle2 size={16} className="icon-green" />, label: "Threat Level: Low" },
    elevated: { icon: <AlertTriangle size={16} className="icon-amber" />, label: "Threat Level: Elevated" },
    high: { icon: <AlertTriangle size={16} className="icon-orange" />, label: "Threat Level: High" },
    critical: { icon: <ShieldAlert size={16} className="icon-red" />, label: "Threat Level: Critical" },
  };

  const conf = config[level] || config.low;

  return (
    <div className={`threat-banner level-${level}`}>
      <span className="threat-banner-icon">{conf.icon}</span>
      <div className="threat-banner-content">
        <div className="threat-banner-level">{conf.label}</div>
        <div className="threat-banner-desc">{description}</div>
      </div>
    </div>
  );
}

/* ── Quick Actions Panel ──────────────────────────────── */

function QuickActionsPanel() {
  const actions = [
    { icon: <Video size={20} className="icon-blue" />, label: "Analyze Video", desc: "Deepfake & transcript", href: "/investigate" },
    { icon: <ImageIcon size={20} className="icon-purple" />, label: "Scan Image", desc: "Forgery & ELA check", href: "/investigate" },
    { icon: <Mail size={20} className="icon-amber" />, label: "Check Email", desc: "SPF/DKIM & phishing", href: "/investigate" },
    { icon: <Globe size={20} className="icon-cyan" />, label: "Audit Website", desc: "WHOIS & SSL audit", href: "/investigate" },
  ];

  return (
    <div className="quick-actions-card">
      <div className="quick-actions-header">
        <h3 style={{ gap: 8 }}>
          <Activity size={16} className="icon-purple" />
          Quick Actions
        </h3>
      </div>
      <div className="quick-actions-grid">
        {actions.map((action) => (
          <Link
            key={action.label}
            href={action.href}
            className="quick-action-btn"
          >
            <span className="quick-action-icon" style={{ display: "flex", alignItems: "center" }}>{action.icon}</span>
            <span className="quick-action-label" style={{ marginTop: 4 }}>{action.label}</span>
            <span className="quick-action-desc">{action.desc}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

/* ── Stat Card ────────────────────────────────────────── */

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color?: string;
}) {
  return (
    <div
      style={{
        padding: "18px 20px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 8,
        }}
      >
        <span
          style={{
            fontSize: 11,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            fontWeight: 700,
          }}
        >
          {label}
        </span>
        <span style={{ display: "flex", alignItems: "center" }}>{icon}</span>
      </div>
      <div
        style={{
          fontSize: 26,
          fontWeight: 800,
          color: color || "var(--text-primary)",
        }}
      >
        {value}
      </div>
    </div>
  );
}
