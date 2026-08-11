/**
 * MarketTrust AI — API Client
 *
 * Wraps all backend API endpoints with typed fetch functions.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// ── Types ──────────────────────────────────────────────────

export interface Investigation {
  id: string;
  title: string;
  status: string;
  type: string | null;
  created_at: string;
  updated_at: string;
  communications: Communication[];
  trust_passport: TrustPassport | null;
}

export interface InvestigationSummary {
  id: string;
  title: string;
  status: string;
  type: string | null;
  created_at: string;
  updated_at: string;
  trust_score: number | null;
  risk_level: string | null;
}

export interface Communication {
  id: string;
  media_type: string;
  original_filename: string | null;
  url: string | null;
  processing_status: string;
  processing_step: string | null;
  extracted_text: string | null;
  metadata_json: Record<string, unknown> | null;
  claims: Claim[];
  created_at: string;
}

export interface Claim {
  id: string;
  subject: string;
  predicate: string;
  object: string;
  confidence: number;
  raw_text: string | null;
  category: string | null;
  evidence: Evidence[];
  created_at: string;
}

export interface Evidence {
  id: string;
  source: string;
  source_url: string | null;
  supports: boolean;
  confidence: number;
  explanation: string;
  created_at: string;
}

export interface TrustPassport {
  id: string;
  overall_score: number;
  risk_level: string;
  recommendation: string;
  media_authenticity_score: number;
  claim_verification_score: number;
  source_credibility_score: number;
  evidence_strength_score: number;
  details_json: Record<string, unknown> | null;
  generated_at: string;
}

export interface UploadResponse {
  communication_id: string;
  filename: string;
  media_type: string;
  status: string;
  message: string;
}

// ── API Functions ──────────────────────────────────────────

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

/** Create a new investigation */
export async function createInvestigation(
  title: string,
  type?: string
): Promise<Investigation> {
  return fetchApi<Investigation>("/investigations", {
    method: "POST",
    body: JSON.stringify({ title, type }),
  });
}

/** Create a 1-click sample demo scenario */
export async function createDemoScenario(
  scenarioId: string
): Promise<Investigation> {
  return fetchApi<Investigation>(`/investigations/demo/${scenarioId}`, {
    method: "POST",
  });
}

/** List all investigations */
export async function listInvestigations(
  skip = 0,
  limit = 50
): Promise<InvestigationSummary[]> {
  return fetchApi<InvestigationSummary[]>(
    `/investigations?skip=${skip}&limit=${limit}`
  );
}

/** Get investigation details */
export async function getInvestigation(id: string): Promise<Investigation> {
  return fetchApi<Investigation>(`/investigations/${id}`);
}

/** Upload a media file */
export async function uploadMedia(
  investigationId: string,
  file: File
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/upload`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Upload error: ${res.status}`);
  }

  return res.json();
}

/** Submit a website URL */
export async function submitUrl(
  investigationId: string,
  url: string
): Promise<UploadResponse> {
  return fetchApi<UploadResponse>(
    `/investigations/${investigationId}/url`,
    {
      method: "POST",
      body: JSON.stringify({ url }),
    }
  );
}

/** Get report download URL */
export function getReportUrl(investigationId: string): string {
  return `${API_BASE}/investigations/${investigationId}/report`;
}

/** Delete an investigation */
export async function deleteInvestigation(id: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(`/investigations/${id}`, {
    method: "DELETE",
  });
}

/** Health check */
export async function healthCheck(): Promise<{ status: string; version: string }> {
  return fetchApi("/health");
}

export interface SourceReference {
  investigation_id: string;
  investigation_title: string;
  document_type: string;
  snippet: string;
  risk_level?: string | null;
  trust_score?: number | null;
}

export interface ChatResponse {
  reply: string;
  source: string;
  retrieved_count: number;
  sources: SourceReference[];
  session_id: string;
}

/** Send a chat message to the AI assistant with RAG support & session memory */
export async function sendChatMessage(
  message: string,
  investigationId?: string,
  sessionId?: string
): Promise<ChatResponse> {
  return fetchApi<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      investigation_id: investigationId || null,
      session_id: sessionId || null,
    }),
  });
}

export interface DocumentUploadResponse {
  message: string;
  filename: string;
  chunks_indexed: number;
  status: string;
}

/** Upload a raw text/MD/CSV document directly into ChromaDB RAG store */
export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Document upload error: ${res.status}`);
  }

  return res.json();
}
