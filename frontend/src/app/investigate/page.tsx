"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createInvestigation, uploadMedia, submitUrl } from "@/lib/api";
import UploadZone from "@/components/UploadZone";
import DemoScenarios from "@/components/DemoScenarios";
import DocumentUploader from "@/components/DocumentUploader";
import {
  Video,
  Image as ImageIcon,
  Mail,
  Globe,
  Search,
  Activity,
  PlusCircle,
  FileCheck
} from "lucide-react";

type MediaType = "video" | "image" | "email" | "website";

interface MediaTypeOption {
  type: MediaType;
  icon: React.ReactNode;
  label: string;
  desc: string;
}

export default function InvestigatePage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [mediaType, setMediaType] = useState<MediaType | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaTypes: MediaTypeOption[] = [
    { type: "video", icon: <Video size={28} className="icon-blue" />, label: "Video", desc: "MP4, AVI, MOV" },
    { type: "image", icon: <ImageIcon size={28} className="icon-purple" />, label: "Image", desc: "JPG, PNG, WebP" },
    { type: "email", icon: <Mail size={28} className="icon-amber" />, label: "Email", desc: ".eml files" },
    { type: "website", icon: <Globe size={28} className="icon-cyan" />, label: "Website", desc: "Enter URL" },
  ];

  const acceptMap: Record<MediaType, string> = {
    video: "video/*,.mp4,.avi,.mov,.mkv,.webm",
    image: "image/*,.jpg,.jpeg,.png,.gif,.webp,.bmp",
    email: ".eml,.msg",
    website: "",
  };

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    if (!title.trim()) {
      const cleanName = selectedFile.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      setTitle(`Analysis of ${cleanName}`);
    }
  };

  const handleUrlChange = (newUrl: string) => {
    setUrl(newUrl);
    if (!title.trim() && newUrl.trim()) {
      try {
        const parsed = new URL(newUrl);
        setTitle(`Website Audit: ${parsed.hostname}`);
      } catch {
        setTitle(`Website Audit: ${newUrl}`);
      }
    }
  };

  const canSubmit =
    Boolean(mediaType) &&
    (mediaType === "website" ? Boolean(url.trim()) : Boolean(file));

  const handleSubmit = async () => {
    if (!canSubmit || !mediaType) return;

    setSubmitting(true);
    setError(null);

    const finalTitle =
      title.trim() ||
      (file ? `Analysis of ${file.name}` : "") ||
      (url ? `Website Audit: ${url}` : "") ||
      `Financial Communication Investigation`;

    try {
      const investigation = await createInvestigation(finalTitle, mediaType);

      if (mediaType === "website") {
        await submitUrl(investigation.id, url);
      } else if (file) {
        await uploadMedia(investigation.id, file);
      }

      router.push(`/investigate/${investigation.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start investigation"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 780, margin: "0 auto" }}>
      <div className="page-header">
        <h1>New Investigation</h1>
        <p>Analyze and verify financial media, screenshots, emails, or website links</p>
      </div>

      {/* 1-Click Demo Scenarios */}
      <DemoScenarios onLoading={setSubmitting} />

      {/* Document RAG Indexing Section */}
      <DocumentUploader />

      <div
        style={{
          margin: "24px 0",
          borderTop: "1px solid var(--border)",
          paddingTop: 24,
        }}
      >
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <PlusCircle size={16} className="icon-purple" /> Or Upload Your Own Media
        </h3>

        {/* Title */}
        <div className="form-group">
          <label className="form-label" htmlFor="inv-title">
            Investigation Title
          </label>
          <input
            id="inv-title"
            className="form-input"
            type="text"
            placeholder="e.g., WhatsApp stock tip video promoting 40% guaranteed returns"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={500}
          />
        </div>

        {/* Media Type Selector */}
        <div className="form-group">
          <label className="form-label">Select Media Type</label>
          <div className="media-type-grid">
            {mediaTypes.map((mt) => (
              <button
                key={mt.type}
                className={`media-type-btn ${mediaType === mt.type ? "selected" : ""}`}
                onClick={() => {
                  setMediaType(mt.type);
                  setFile(null);
                  setUrl("");
                }}
                type="button"
              >
                <span className="icon" style={{ display: "flex", alignItems: "center" }}>{mt.icon}</span>
                <span className="label" style={{ marginTop: 6 }}>{mt.label}</span>
                <span style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                  {mt.desc}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Upload Zone or URL Input */}
        {mediaType && (
          <div className="form-group">
            {mediaType === "website" ? (
              <>
                <label className="form-label" htmlFor="inv-url">
                  Website URL
                </label>
                <input
                  id="inv-url"
                  className="form-input"
                  type="url"
                  placeholder="https://example.com/suspicious-investment-offer"
                  value={url}
                  onChange={(e) => handleUrlChange(e.target.value)}
                />
              </>
            ) : (
              <>
                <label className="form-label">Upload File</label>
                <UploadZone
                  onFileSelected={handleFileSelect}
                  accept={acceptMap[mediaType]}
                  mediaType={mediaType}
                />
              </>
            )}
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div
            style={{
              padding: "12px 16px",
              background: "rgba(220, 38, 38, 0.08)",
              border: "1px solid rgba(220, 38, 38, 0.25)",
              borderRadius: "var(--radius-sm)",
              color: "#dc2626",
              marginBottom: 20,
              fontSize: 14,
            }}
          >
            {error}
          </div>
        )}

        {/* Submit Button */}
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={!canSubmit || submitting}
          style={{ width: "100%", padding: "14px 24px", fontSize: 16, gap: 8 }}
        >
          {submitting ? (
            <>
              <div
                className="spinner"
                style={{ width: 18, height: 18, borderWidth: 2 }}
              />
              Analyzing & Extracting Claims...
            </>
          ) : (
            <>
              <Search size={16} />
              <span>Analyze Communication</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
