import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import ChatBotWrapper from "@/components/ChatBotWrapper";

export const metadata: Metadata = {
  title: "MarketTrust AI — Financial Communication Verifier",
  description:
    "Verify whether a financial communication (video, image, email, website) can be trusted before an investor makes a decision.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {/* Live System Status Ticker */}
        <div className="ticker-bar">
          <div className="ticker-item">
            <span className="pulse-green" />
            <span>SYSTEM: ONLINE</span>
          </div>
          <div className="ticker-item">
            <span>SEBI COMPLIANCE ENGINE v1.2</span>
          </div>
          <div className="ticker-item">
            <span>OLLAMA LLM: READY</span>
          </div>
          <div className="ticker-item">
            <span>THREAT DETECTOR: ACTIVE</span>
          </div>
        </div>

        {/* Navigation Bar */}
        <nav className="nav">
          <div className="nav-inner">
            <Link href="/" className="nav-logo">
              <span className="nav-logo-badge">🛡️</span>
              <span>MarketTrust AI</span>
            </Link>
            <div className="nav-links">
              <Link href="/" className="nav-link">
                Dashboard
              </Link>
              <Link href="/investigate" className="nav-link primary">
                + New Investigation
              </Link>
            </div>
          </div>
        </nav>

        <main className="main">{children}</main>

        {/* Global AI Chatbot Widget */}
        <ChatBotWrapper />
      </body>
    </html>
  );
}
