"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createDemoScenario } from "@/lib/api";
import { Video, Image as ImageIcon, Mail, Globe, Sparkles } from "lucide-react";

interface DemoScenariosProps {
  onLoading?: (isLoading: boolean) => void;
}

const DEMO_ITEMS = [
  {
    id: "video_deepfake",
    title: "Deepfake Stock Tip Video",
    desc: "Guaranteed 45% Monthly Return with Fake SEBI Reg INZ00099999",
    type: "VIDEO",
    risk: "CRITICAL",
    badgeColor: "#dc2626",
  },
  {
    id: "image_pnl_forgery",
    title: "Photoshopped P&L Statement",
    desc: "Manipulated Zerodha Profit Screenshot (₹48 Lakhs) with ELA tampering",
    type: "IMAGE",
    risk: "CRITICAL",
    badgeColor: "#dc2626",
  },
  {
    id: "email_phishing",
    title: "Spoofed SEBI IPO Allotment Email",
    desc: "Direct IPO allotment offer at 60% discount via UPI transfer",
    type: "EMAIL",
    risk: "CRITICAL",
    badgeColor: "#dc2626",
  },
  {
    id: "legitimate_broker",
    title: "Legitimate Broker Note (ICICI)",
    desc: "Authentic SEBI Registered Research Note with proper disclosures",
    type: "WEBSITE",
    risk: "LOW RISK",
    badgeColor: "#059669",
  },
];

export default function DemoScenarios({ onLoading }: DemoScenariosProps) {
  const router = useRouter();
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const handleSelectDemo = async (scenarioId: string) => {
    setLoadingId(scenarioId);
    if (onLoading) onLoading(true);

    try {
      const inv = await createDemoScenario(scenarioId);
      router.push(`/investigate/${inv.id}`);
    } catch (err) {
      console.error("Demo creation failed:", err);
    } finally {
      setLoadingId(null);
      if (onLoading) onLoading(false);
    }
  };

  const getDemoIcon = (id: string) => {
    switch (id) {
      case "video_deepfake":
        return <Video size={22} className="icon-blue" />;
      case "image_pnl_forgery":
        return <ImageIcon size={22} className="icon-purple" />;
      case "email_phishing":
        return <Mail size={22} className="icon-amber" />;
      case "legitimate_broker":
        return <Globe size={22} className="icon-green" />;
      default:
        return <Sparkles size={22} className="icon-cyan" />;
    }
  };

  return (
    <div style={{ margin: "24px 0" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <span
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: "var(--accent-cyan)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            display: "flex",
            alignItems: "center",
            gap: 6
          }}
        >
          <Sparkles size={14} /> Quick Demo Scenarios (1-Click Test Cases)
        </span>
        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
          No file upload needed
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 12,
        }}
      >
        {DEMO_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => handleSelectDemo(item.id)}
            disabled={loadingId !== null}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              padding: "14px 16px",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
              opacity: loadingId !== null && loadingId !== item.id ? 0.5 : 1,
            }}
            className="demo-card-hover"
          >
            <span style={{ flexShrink: 0, marginTop: 4, display: "flex", alignItems: "center" }}>
              {getDemoIcon(item.id)}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 4,
                }}
              >
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 700,
                    color: "var(--text-primary)",
                  }}
                >
                  {item.title}
                </span>
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 800,
                    padding: "2px 6px",
                    borderRadius: 4,
                    color: item.badgeColor,
                    background: item.badgeColor + "18",
                    border: `1px solid ${item.badgeColor}33`,
                  }}
                >
                  {item.risk}
                </span>
              </div>
              <p
                style={{
                  fontSize: 11,
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                  margin: 0,
                }}
              >
                {item.desc}
              </p>
            </div>
            {loadingId === item.id && (
              <div
                className="spinner"
                style={{ width: 14, height: 14, borderWidth: 2, flexShrink: 0 }}
              />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
