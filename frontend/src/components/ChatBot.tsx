"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { sendChatMessage, SourceReference } from "@/lib/api";
import { MessageCircle, X, Send, Bot, User, Sparkles, Database, ExternalLink, Maximize2, Minimize2, Zap } from "lucide-react";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  source?: string;
  sources?: SourceReference[];
  timestamp: Date;
}

export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true); // Default to full right-side panel
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "👋 Hi! I'm the **MarketTrust AI Assistant** with **Vector RAG**. Ask me about investigation results, trust scores, SEBI regulations, or fraud indicators across your database.",
      source: "system",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const params = useParams();

  // Auto-detect investigation context from URL
  const investigationId = params?.id as string | undefined;

  // Initialize unique session ID once on mount
  useEffect(() => {
    setSessionId(`session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 200);
    }
  }, [isOpen]);

  const handleSend = async (customMessage?: string) => {
    const textToSend = customMessage || input.trim();
    if (!textToSend || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: textToSend,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customMessage) setInput("");
    setIsLoading(true);

    try {
      const response = await sendChatMessage(textToSend, investigationId, sessionId);
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.reply,
        source: response.source,
        sources: response.sources,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content:
          "⚠️ Unable to connect to the AI assistant. Please ensure the backend server is running.",
        source: "error",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Enhanced markdown rendering for structured, human-readable formatting
  const renderFormattedText = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} style={{ color: "var(--text-primary)", fontWeight: 700 }}>
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={i}
            style={{
              background: "rgba(6, 182, 212, 0.15)",
              border: "1px solid rgba(6, 182, 212, 0.3)",
              padding: "1px 6px",
              borderRadius: "4px",
              fontSize: "11px",
              color: "var(--accent-cyan)",
              fontFamily: "monospace",
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  const renderContent = (content: string) => {
    const lines = content.split("\n");
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) return <div key={idx} style={{ height: "4px" }} />;

          // Headings (## or ###)
          if (trimmed.startsWith("###") || trimmed.startsWith("##")) {
            const headerText = trimmed.replace(/^#+\s*/, "");
            return (
              <div
                key={idx}
                style={{
                  fontSize: "13px",
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  marginTop: "6px",
                  marginBottom: "2px",
                  borderBottom: "1px solid rgba(255,255,255,0.08)",
                  paddingBottom: "4px",
                }}
              >
                {renderFormattedText(headerText)}
              </div>
            );
          }

          // Indented sub-bullets (▫)
          if (trimmed.startsWith("▫") || trimmed.startsWith("  ▫")) {
            return (
              <div
                key={idx}
                style={{
                  paddingLeft: "14px",
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  lineHeight: "1.5",
                }}
              >
                {renderFormattedText(trimmed)}
              </div>
            );
          }

          // Primary bullets (• or - or *)
          if (trimmed.startsWith("•") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  gap: "6px",
                  fontSize: "12.5px",
                  lineHeight: "1.5",
                  marginTop: "2px",
                }}
              >
                <span style={{ color: "var(--accent-purple)", fontWeight: 700 }}>•</span>
                <span>{renderFormattedText(trimmed.replace(/^([•\-\*]\s*)/, ""))}</span>
              </div>
            );
          }

          // Regular paragraph lines
          return (
            <div key={idx} style={{ fontSize: "12.5px", lineHeight: "1.5" }}>
              {renderFormattedText(line)}
            </div>
          );
        })}
      </div>
    );
  };

  const renderRiskBadge = (level?: string | null) => {
    if (!level) return null;
    const l = level.toLowerCase();
    let bg = "rgba(100, 116, 139, 0.2)";
    let color = "#94a3b8";
    if (l === "critical" || l === "high") {
      bg = "rgba(239, 68, 68, 0.2)";
      color = "#ef4444";
    } else if (l === "medium") {
      bg = "rgba(245, 158, 11, 0.2)";
      color = "#f59e0b";
    } else if (l === "low") {
      bg = "rgba(16, 185, 129, 0.2)";
      color = "#10b981";
    }
    return (
      <span
        style={{
          background: bg,
          color: color,
          fontSize: "10px",
          fontWeight: 700,
          padding: "2px 6px",
          borderRadius: "4px",
          textTransform: "uppercase",
        }}
      >
        {level}
      </span>
    );
  };

  return (
    <>
      {/* Floating Toggle Button */}
      <button
        className={`chatbot-toggle ${isOpen ? "active" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? "Close chat" : "Open AI assistant"}
      >
        {isOpen ? <X size={22} /> : <MessageCircle size={22} />}
        {!isOpen && <span className="chatbot-toggle-pulse" />}
      </button>

      {/* Chat Window / Side Panel */}
      {isOpen && (
        <div className={`chatbot-window ${isExpanded ? "expanded-side-panel" : ""}`}>
          {/* Header */}
          <div className="chatbot-header">
            <div className="chatbot-header-left">
              <div className="chatbot-avatar">
                <Bot size={18} />
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span className="chatbot-header-title">MarketTrust RAG</span>
                  <span className="rag-pill">
                    <Zap size={10} /> Groq & Vector Engine
                  </span>
                </div>
                <div className="chatbot-header-status">
                  <span className="chatbot-status-dot" />
                  {investigationId ? "Investigation Context Active" : "Global Knowledge Base"}
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <button
                className="chatbot-close"
                onClick={() => setIsExpanded(!isExpanded)}
                title={isExpanded ? "Collapse to Floating Box" : "Expand to Full Right Side Panel"}
                aria-label="Toggle panel expand"
              >
                {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>
              <button
                className="chatbot-close"
                onClick={() => setIsOpen(false)}
                title="Close chat"
                aria-label="Close chat"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="chatbot-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`chatbot-msg ${msg.role}`}>
                <div className="chatbot-msg-icon">
                  {msg.role === "assistant" ? <Sparkles size={14} /> : <User size={14} />}
                </div>
                <div className="chatbot-msg-bubble">
                  <div className="chatbot-msg-content">{renderContent(msg.content)}</div>

                  {/* Render Sources / Citations if available */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="chatbot-sources-box">
                      <div className="chatbot-sources-title">
                        <Database size={11} /> Retrived RAG Citations ({msg.sources.length}):
                      </div>
                      <div className="chatbot-sources-list">
                        {msg.sources.map((src, idx) => (
                          <Link
                            key={idx}
                            href={`/investigate/${src.investigation_id}`}
                            className="chatbot-source-card"
                          >
                            <div className="chatbot-source-card-header">
                              <span className="chatbot-source-card-title">{src.investigation_title}</span>
                              {renderRiskBadge(src.risk_level)}
                              <ExternalLink size={10} className="chatbot-source-link-icon" />
                            </div>
                            <div className="chatbot-source-card-meta">
                              <span className="chatbot-source-doc-type">
                                {src.document_type.replace("_", " ")}
                              </span>
                              {src.trust_score !== undefined && src.trust_score !== null && (
                                <span>Score: {src.trust_score}/100</span>
                              )}
                            </div>
                            <div className="chatbot-source-snippet">"{src.snippet}"</div>
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}

                  {msg.source && msg.role === "assistant" && msg.source !== "system" && (
                    <div className="chatbot-msg-source">via {msg.source}</div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing Indicator */}
            {isLoading && (
              <div className="chatbot-msg assistant">
                <div className="chatbot-msg-icon">
                  <Sparkles size={14} />
                </div>
                <div className="chatbot-msg-bubble">
                  <div className="chatbot-typing">
                    <span />
                    <span />
                    <span />
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "8px" }}>
                    Searching ChromaDB & reasoning...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts (if chat is short) */}
          {messages.length <= 2 && !isLoading && (
            <div className="chatbot-quick-prompts">
              <button
                className="quick-prompt-chip"
                onClick={() => handleSend("What investigations are high or critical risk?")}
              >
                🚨 Critical risk cases
              </button>
              <button
                className="quick-prompt-chip"
                onClick={() => handleSend("Show extracted claims mentioning SEBI")}
              >
                🏛️ SEBI claims
              </button>
              <button
                className="quick-prompt-chip"
                onClick={() => handleSend("How does evidence verification work?")}
              >
                🔍 Verification engine
              </button>
            </div>
          )}

          {/* Input */}
          <div className="chatbot-input-area">
            <input
              ref={inputRef}
              type="text"
              className="chatbot-input"
              placeholder="Ask about investigations, SEBI rules, trust scores..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              maxLength={2000}
            />
            <button
              className="chatbot-send"
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
