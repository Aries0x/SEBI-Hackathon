"""
MarketTrust AI — RAG Chat API Endpoint.

Full Retrieval-Augmented Generation chatbot that:
1. Semantically searches ChromaDB (investigations_rag) for relevant context
2. Queries the SQL database for investigation details and keyword matches
3. Maintains per-session conversation memory
4. Returns source citations so the frontend can render clickable reference cards
5. Generates grounded responses via Ollama/Qwen3 with heuristic fallback
"""

from __future__ import annotations

import logging
import uuid
import time
import threading
from collections import OrderedDict
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.config import settings
from app.database.models import (
    Claim,
    Communication,
    Evidence,
    Investigation,
    TrustPassport,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# ── System prompt for the MarketTrust AI RAG assistant ──────

SYSTEM_PROMPT = """\
You are MarketTrust AI Assistant — a financial communication verification expert \
specializing in Indian capital markets and SEBI (Securities and Exchange Board of India) compliance.

Your role:
- Help users understand their investigation results, trust scores, and evidence.
- Answer questions by referencing REAL investigation data retrieved from the database.
- Explain SEBI regulations, red flags in financial communications, and fraud patterns.
- Be concise, professional, and accurate. Use bullet points for clarity.
- Always ground your answers in the retrieved investigation data when available.
- If you don't know something, say so rather than guessing.
- Never provide investment advice. Always recommend consulting a registered SEBI advisor.
- When referencing specific investigations or evidence, include the investigation title \
  so that users can verify the source.

Key system context:
- MarketTrust AI verifies financial communications (videos, images, emails, websites).
- It extracts claims, verifies them via ChromaDB knowledge base, LLM reasoning, \
  WHOIS/SSL checks, Google Safe Browsing, and SEBI red flag heuristics.
- Trust scores range from 0-100 (higher = more trustworthy).
- Risk levels: low, medium, high, critical.
"""


# ── Conversation Memory Store ───────────────────────────────


class _MemoryMessage:
    """A single message in conversation history."""

    __slots__ = ("role", "content", "timestamp")

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content
        self.timestamp = time.time()


class ConversationMemory:
    """
    Thread-safe in-memory conversation store.

    Keyed by session_id.  Each session keeps the last *max_messages*
    exchanges and auto-expires after *ttl_seconds* of inactivity.
    """

    def __init__(
        self, max_messages: int = 20, ttl_seconds: int = 3600, max_sessions: int = 500
    ) -> None:
        self._store: OrderedDict[str, List[_MemoryMessage]] = OrderedDict()
        self._lock = threading.Lock()
        self._max_messages = max_messages
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions

    def add(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            self._evict_expired()
            if session_id not in self._store:
                if len(self._store) >= self._max_sessions:
                    self._store.popitem(last=False)
                self._store[session_id] = []
            msgs = self._store[session_id]
            msgs.append(_MemoryMessage(role, content))
            if len(msgs) > self._max_messages:
                self._store[session_id] = msgs[-self._max_messages :]
            self._store.move_to_end(session_id)

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        with self._lock:
            msgs = self._store.get(session_id, [])
            return [{"role": m.role, "content": m.content} for m in msgs]

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid
            for sid, msgs in self._store.items()
            if msgs and (now - msgs[-1].timestamp) > self._ttl
        ]
        for sid in expired:
            del self._store[sid]


# Singleton memory store
_memory = ConversationMemory()


# ── Request / Response schemas ──────────────────────────────


class ChatRequest(BaseModel):
    """Chat message from the user."""

    message: str = Field(..., min_length=1, max_length=2000)
    investigation_id: Optional[str] = None
    session_id: Optional[str] = None


class SourceReference(BaseModel):
    """A source document the chatbot used to form its answer."""

    investigation_id: str
    investigation_title: str
    document_type: str  # "claim" | "evidence" | "extracted_text" | "trust_passport"
    snippet: str
    risk_level: Optional[str] = None
    trust_score: Optional[float] = None


class ChatResponse(BaseModel):
    """Chat response from the assistant."""

    reply: str
    source: str = "ollama"
    retrieved_count: int = 0
    sources: List[SourceReference] = []
    session_id: str = ""


# ── POST /api/chat ──────────────────────────────────────────


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the MarketTrust AI RAG assistant."""

    session_id = body.session_id or str(uuid.uuid4())

    # Record user message in memory
    _memory.add(session_id, "user", body.message)

    # ── RAG Step 1: Retrieve relevant context ──
    rag_context, retrieved_count, sources = await _retrieve_context(
        db, body.message, body.investigation_id
    )

    system_prompt = SYSTEM_PROMPT
    if rag_context:
        system_prompt += "\n\n--- RETRIEVED INVESTIGATION DATA (from database & knowledge base) ---\n"
        system_prompt += rag_context
        system_prompt += "\n--- END OF RETRIEVED DATA ---\n"
        system_prompt += (
            "\nUse the above retrieved data to answer the user's question. "
            "Reference specific investigation titles, trust scores, claims, "
            "and evidence when relevant. If the data doesn't contain the answer, "
            "say so and provide general guidance instead."
        )

    # ── RAG Step 2: Build conversation history ──
    history = _memory.get_history(session_id)

    # ── RAG Step 3: Generate response via LLM (Groq / Ollama / Heuristic) ──
    reply, llm_source = await _query_llm(system_prompt, body.message, history)
    if reply and llm_source != "heuristic":
        _memory.add(session_id, "assistant", reply)
        return ChatResponse(
            reply=reply,
            source=llm_source,
            retrieved_count=retrieved_count,
            sources=sources,
            session_id=session_id,
        )

    # ── Fallback: Heuristic response with DB context ──
    reply = _heuristic_response(body.message, rag_context, retrieved_count)
    _memory.add(session_id, "assistant", reply)
    return ChatResponse(
        reply=reply,
        source="heuristic",
        retrieved_count=retrieved_count,
        sources=sources,
        session_id=session_id,
    )


# ── RAG Retrieval Engine ────────────────────────────────────


async def _retrieve_context(
    db: AsyncSession,
    user_message: str,
    investigation_id: Optional[str] = None,
) -> tuple[str, int, List[SourceReference]]:
    """
    Retrieve relevant investigation data using multiple strategies.

    Strategy order:
    1. ChromaDB semantic search (vector similarity)
    2. Specific investigation detail (if investigation_id provided)
    3. SQL keyword search (fallback/supplement)
    4. Aggregate statistics

    Returns (context_string, num_items_retrieved, source_references).
    """
    context_parts: List[str] = []
    retrieved_count = 0
    sources: List[SourceReference] = []

    # ── Strategy 1: ChromaDB semantic search (NEW) ──────────
    semantic_context, semantic_sources = _semantic_search(
        user_message, investigation_id
    )
    if semantic_context:
        context_parts.append(semantic_context)
        sources.extend(semantic_sources)
        retrieved_count += len(semantic_sources)

    # ── Strategy 2: Load specific investigation (full detail) ──
    if investigation_id:
        try:
            inv_uuid = uuid.UUID(investigation_id)
            detail, detail_source = await _load_investigation_detail(db, inv_uuid)
            if detail:
                context_parts.append(detail)
                retrieved_count += 1
                if detail_source and not any(s.investigation_id == detail_source.investigation_id for s in sources):
                    sources.append(detail_source)
        except (ValueError, Exception) as e:
            logger.warning(f"Could not load specific investigation: {e}")

    # ── Strategy 3: Load all recent investigations (summaries) ──
    recent_summary = await _load_recent_investigations_summary(db)
    if recent_summary:
        context_parts.append(recent_summary)
        retrieved_count += 1

    # ── Strategy 4: Keyword search across claims and evidence ──
    keyword_hits = await _search_claims_and_evidence(db, user_message)
    if keyword_hits:
        context_parts.append(keyword_hits)
        retrieved_count += 1

    # ── Strategy 5: Aggregate statistics ──
    stats = await _load_aggregate_stats(db)
    if stats:
        context_parts.append(stats)
        retrieved_count += 1

    return "\n\n".join(context_parts), retrieved_count, sources


def _semantic_search(
    query: str,
    investigation_id: Optional[str] = None,
) -> tuple[str, List[SourceReference]]:
    """
    Search ChromaDB ``investigations_rag`` collection for semantically
    relevant investigation data.

    Returns (formatted_context, source_references).
    """
    try:
        from app.chat.rag_indexer import search_rag

        hits = search_rag(
            query=query,
            n_results=8,
            investigation_id=investigation_id,
        )
    except Exception as e:
        logger.warning("Semantic search failed: %s", e)
        return "", []

    if not hits:
        return "", []

    lines = [f"## SEMANTIC SEARCH RESULTS ({len(hits)} relevant matches):"]
    sources: List[SourceReference] = []
    seen_ids = set()

    for hit in hits:
        meta = hit.get("metadata", {})
        doc = hit.get("document", "")
        confidence = hit.get("confidence", 0)
        doc_type = meta.get("document_type", "unknown")
        inv_id = meta.get("investigation_id", "")
        inv_title = meta.get("investigation_title", "Unknown")
        risk = meta.get("risk_level")
        score = meta.get("trust_score")

        # Format for context
        type_label = doc_type.replace("_", " ").title()
        lines.append(
            f"  • [{type_label}] (relevance: {confidence:.0%}) "
            f"from \"{inv_title}\": {doc[:300]}"
        )

        # Build source reference (deduplicated by inv_id + doc_type)
        dedup_key = f"{inv_id}:{doc_type}:{meta.get('claim_id', '')}:{meta.get('evidence_id', '')}"
        if dedup_key not in seen_ids and inv_id:
            seen_ids.add(dedup_key)
            sources.append(
                SourceReference(
                    investigation_id=inv_id,
                    investigation_title=inv_title,
                    document_type=doc_type,
                    snippet=doc[:150],
                    risk_level=risk,
                    trust_score=float(score) if score is not None else None,
                )
            )

    return "\n".join(lines), sources


async def _load_investigation_detail(
    db: AsyncSession, investigation_id: uuid.UUID
) -> tuple[Optional[str], Optional[SourceReference]]:
    """Load full details of a specific investigation."""
    result = await db.execute(
        select(Investigation)
        .where(Investigation.id == investigation_id)
        .options(
            selectinload(Investigation.communications)
            .selectinload(Communication.claims)
            .selectinload(Claim.evidence),
            selectinload(Investigation.trust_passport),
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        return None, None

    passport = inv.trust_passport
    lines = [
        f"## CURRENT INVESTIGATION (User is viewing this):",
        f"- Title: {inv.title}",
        f"- Type: {(inv.type or 'unknown').upper()}",
        f"- Status: {inv.status.upper()}",
        f"- Created: {inv.created_at}",
    ]

    if passport:
        lines.extend([
            f"- Trust Score: {passport.overall_score}/100",
            f"- Risk Level: {passport.risk_level.upper()}",
            f"- Media Authenticity: {passport.media_authenticity_score}/100",
            f"- Claim Verification: {passport.claim_verification_score}/100",
            f"- Source Credibility: {passport.source_credibility_score}/100",
            f"- Evidence Strength: {passport.evidence_strength_score}/100",
            f"- Recommendation: {passport.recommendation}",
        ])

    # Collect all claims and evidence
    all_claims = []
    for comm in (inv.communications or []):
        if comm.extracted_text:
            lines.append(f"\nExtracted Text (first 500 chars): {comm.extracted_text[:500]}")
        for claim in (comm.claims or []):
            all_claims.append(claim)

    if all_claims:
        lines.append(f"\n### Claims ({len(all_claims)} total):")
        for i, c in enumerate(all_claims[:15], 1):
            ev_list = c.evidence or []
            supporting = sum(1 for e in ev_list if e.supports)
            contradicting = len(ev_list) - supporting
            lines.append(
                f"  {i}. [{c.category or 'general'}] "
                f"{c.subject} → {c.predicate} → {c.object} "
                f"(confidence: {c.confidence:.0%}, "
                f"evidence: {supporting} supporting / {contradicting} contradicting)"
            )
            for ev in ev_list[:3]:
                verdict = "✅ SUPPORTS" if ev.supports else "❌ CONTRADICTS"
                lines.append(
                    f"      → {verdict} ({ev.confidence:.0%}) via {ev.source}: {ev.explanation[:200]}"
                )

    source_ref = SourceReference(
        investigation_id=str(inv.id),
        investigation_title=inv.title,
        document_type="investigation",
        snippet=passport.recommendation[:150] if passport else f"Investigation: {inv.title}",
        risk_level=passport.risk_level if passport else None,
        trust_score=passport.overall_score if passport else None,
    )

    return "\n".join(lines), source_ref


async def _load_recent_investigations_summary(db: AsyncSession) -> Optional[str]:
    """Load summary of all investigations (most recent first)."""
    result = await db.execute(
        select(Investigation)
        .options(
            selectinload(Investigation.trust_passport),
            selectinload(Investigation.communications)
            .selectinload(Communication.claims),
        )
        .order_by(Investigation.created_at.desc())
        .limit(20)
    )
    investigations = result.scalars().all()

    if not investigations:
        return None

    lines = [f"### 📋 Recent Audits & Investigations ({len(investigations)} Records)"]

    for inv in investigations:
        passport = inv.trust_passport
        claim_count = sum(
            len(comm.claims or []) for comm in (inv.communications or [])
        )
        score = f"{passport.overall_score:.0f}/100" if passport else "N/A"
        risk = passport.risk_level.lower() if passport else "pending"

        risk_icon = "⚪"
        if risk == "critical":
            risk_icon = "🚨 CRITICAL"
        elif risk == "high":
            risk_icon = "⚠️ HIGH"
        elif risk == "medium":
            risk_icon = "⚡ MEDIUM"
        elif risk == "low":
            risk_icon = "✅ LOW"

        media_type = (inv.type or "media").upper()
        lines.append(
            f"• **{inv.title}**\n"
            f"  ▫ Channel: `{media_type}` | Risk: {risk_icon} | Trust Score: **{score}** | Claims: **{claim_count}**"
        )

    return "\n\n".join(lines)


async def _search_claims_and_evidence(
    db: AsyncSession, user_message: str
) -> Optional[str]:
    """Search claims and evidence for keywords from the user's message."""
    # Extract meaningful keywords (skip very common short words)
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "what", "how", "why",
        "who", "when", "where", "can", "do", "does", "did", "will", "would",
        "should", "could", "this", "that", "it", "its", "for", "and", "or",
        "but", "in", "on", "at", "to", "of", "with", "from", "by", "about",
        "me", "my", "i", "you", "your", "tell", "show", "give", "get",
        "make", "made", "has", "have", "had", "not", "no", "all", "any",
    }

    words = [
        w.strip("?.,!\"'()[]")
        for w in user_message.lower().split()
        if len(w.strip("?.,!\"'()[]")) > 2
    ]
    keywords = [w for w in words if w not in stop_words]

    if not keywords:
        return None

    # Search claims
    matching_claims = []
    for keyword in keywords[:5]:  # Limit to 5 keywords
        pattern = f"%{keyword}%"
        result = await db.execute(
            select(Claim)
            .options(selectinload(Claim.evidence))
            .where(
                (Claim.subject.ilike(pattern))
                | (Claim.predicate.ilike(pattern))
                | (Claim.object.ilike(pattern))
                | (Claim.raw_text.ilike(pattern))
                | (Claim.category.ilike(pattern))
            )
            .limit(10)
        )
        claims = result.scalars().all()
        for c in claims:
            if c.id not in {mc.id for mc in matching_claims}:
                matching_claims.append(c)

    # Search evidence explanations
    matching_evidence = []
    for keyword in keywords[:5]:
        pattern = f"%{keyword}%"
        result = await db.execute(
            select(Evidence)
            .where(
                (Evidence.explanation.ilike(pattern))
                | (Evidence.source.ilike(pattern))
            )
            .limit(10)
        )
        evidences = result.scalars().all()
        for ev in evidences:
            if ev.id not in {me.id for me in matching_evidence}:
                matching_evidence.append(ev)

    if not matching_claims and not matching_evidence:
        return None

    lines = [f"## KEYWORD SEARCH RESULTS (searched for: {', '.join(keywords)}):"]

    if matching_claims:
        lines.append(f"\n### Matching Claims ({len(matching_claims)}):")
        for c in matching_claims[:10]:
            ev_list = c.evidence or []
            supporting = sum(1 for e in ev_list if e.supports)
            lines.append(
                f"  • [{c.category or 'general'}] {c.subject} → {c.predicate} → {c.object} "
                f"(confidence: {c.confidence:.0%}, "
                f"evidence: {supporting}/{len(ev_list)} supporting)"
            )
            for ev in ev_list[:2]:
                verdict = "✅" if ev.supports else "❌"
                lines.append(f"    {verdict} {ev.source}: {ev.explanation[:150]}")

    if matching_evidence:
        lines.append(f"\n### Matching Evidence ({len(matching_evidence)}):")
        for ev in matching_evidence[:10]:
            verdict = "✅ SUPPORTS" if ev.supports else "❌ CONTRADICTS"
            lines.append(
                f"  • {verdict} ({ev.confidence:.0%}) via {ev.source}: "
                f"{ev.explanation[:200]}"
            )

    return "\n".join(lines)


async def _load_aggregate_stats(db: AsyncSession) -> Optional[str]:
    """Load aggregate statistics across all investigations."""
    # Count investigations by status
    result = await db.execute(
        select(
            Investigation.status,
            sa_func.count(Investigation.id)
        ).group_by(Investigation.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}

    # Count investigations by risk level
    result = await db.execute(
        select(
            TrustPassport.risk_level,
            sa_func.count(TrustPassport.id)
        ).group_by(TrustPassport.risk_level)
    )
    risk_counts = {row[0]: row[1] for row in result.all()}

    # Average trust score
    result = await db.execute(
        select(sa_func.avg(TrustPassport.overall_score))
    )
    avg_score = result.scalar()

    # Total claims and evidence
    result = await db.execute(select(sa_func.count(Claim.id)))
    total_claims = result.scalar() or 0

    result = await db.execute(select(sa_func.count(Evidence.id)))
    total_evidence = result.scalar() or 0

    result = await db.execute(
        select(sa_func.count(Evidence.id)).where(Evidence.supports == True)
    )
    supporting_evidence = result.scalar() or 0

    total_investigations = sum(status_counts.values())

    if total_investigations == 0:
        return "## DATABASE STATS:\nNo investigations found in the database yet."

    lines = [
        "## DATABASE STATISTICS:",
        f"- Total Investigations: {total_investigations}",
        f"- By Status: {', '.join(f'{s}: {c}' for s, c in status_counts.items())}",
        f"- By Risk Level: {', '.join(f'{r}: {c}' for r, c in risk_counts.items()) if risk_counts else 'N/A'}",
        f"- Average Trust Score: {avg_score:.1f}/100" if avg_score else "- Average Trust Score: N/A",
        f"- Total Claims Extracted: {total_claims}",
        f"- Total Evidence Items: {total_evidence} ({supporting_evidence} supporting, {total_evidence - supporting_evidence} contradicting)",
    ]

    return "\n".join(lines)


# ── LLM Query Engine (Groq / Ollama / Dispatcher) ────────────


async def _query_groq(
    system_prompt: str,
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """
    Query Groq Cloud API with RAG context and conversation history.
    Uses GROQ_API_KEY from environment or settings.
    """
    import os

    api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.debug("GROQ_API_KEY not configured")
        return None

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            prior = history[:-1] if history else []
            for msg in prior[-10:]:
                messages.append(msg)

        messages.append({"role": "user", "content": user_message})

        completion = client.chat.completions.create(
            model=settings.groq_model or "llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=1500,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq API query failed: {e}")
        return None


async def _query_llm(
    system_prompt: str,
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> tuple[Optional[str], str]:
    """
    Query available LLM provider according to settings.llm_provider.
    Returns (reply_text, provider_name).
    """
    provider = (settings.llm_provider or "auto").lower()

    if provider == "groq":
        reply = await _query_groq(system_prompt, user_message, history)
        if reply:
            return reply, "groq (Llama 3.3 70B)"

    if provider == "ollama":
        reply = await _query_ollama(system_prompt, user_message, history)
        if reply:
            return reply, "ollama (Qwen3)"

    # Auto mode: try Groq first (if key set), then Ollama
    reply = await _query_groq(system_prompt, user_message, history)
    if reply:
        return reply, "groq (Llama 3.3 70B)"

    reply = await _query_ollama(system_prompt, user_message, history)
    if reply:
        return reply, "ollama (Qwen3)"

    return None, "heuristic"


async def _query_ollama(
    system_prompt: str,
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """
    Query the local Ollama LLM with RAG context and conversation history.

    The history list contains prior messages in ``{"role": ..., "content": ...}``
    format.  We include up to the last 10 messages for context.
    """
    try:
        import ollama  # type: ignore

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 10 exchanges)
        if history:
            # Skip the very last user message since we add it explicitly below
            prior = history[:-1] if history else []
            for msg in prior[-10:]:
                messages.append(msg)

        messages.append({"role": "user", "content": user_message})

        response = ollama.chat(
            model=settings.ollama_model,
            messages=messages,
            options={"temperature": 0.3, "num_predict": 1500},
        )
        return response["message"]["content"].strip()

    except ImportError:
        logger.debug("Ollama package not available")
        return None
    except Exception as e:
        logger.warning(f"Ollama query failed: {e}")
        return None


# ── Heuristic Fallback (DB-aware) ──────────────────────────


def _heuristic_response(
    message: str,
    rag_context: str,
    retrieved_count: int,
) -> str:
    """Generate a heuristic response that prioritizes topic-specific answers, supplemented by DB data."""
    msg = message.lower()

    # ── Helper: append truncated RAG context as supplementary data ──
    def _with_rag_supplement(base_reply: str, max_chars: int = 800) -> str:
        if not rag_context or retrieved_count == 0:
            return base_reply
        # Extract just investigation summaries from the RAG context (skip raw headers)
        clean = rag_context.replace("```", "").strip()
        supplement = clean[:max_chars]
        if len(clean) > max_chars:
            supplement += "…"
        return (
            f"{base_reply}\n\n"
            f"---\n"
            f"📊 **Related Data from Your Investigations** ({retrieved_count} sources):\n\n"
            f"{supplement}"
        )

    # ── Topic-specific heuristic answers (checked FIRST) ──

    if any(w in msg for w in ["sebi", "regulation", "registered", "compliance"]):
        reply = (
            "**SEBI (Securities and Exchange Board of India)** is the regulatory authority "
            "for securities markets in India.\n\n"
            "Key points:\n"
            "- All stock brokers, investment advisors, and portfolio managers must be SEBI-registered\n"
            "- Guaranteed return promises are **prohibited** under SEBI regulations\n"
            "- Investment advice via unregistered WhatsApp/Telegram channels is **illegal**\n"
            "- You can verify SEBI registration at [sebi.gov.in](https://www.sebi.gov.in/)\n"
            "- SEBI's Investor Grievance portal: [SCORES](https://scores.sebi.gov.in/)\n\n"
            "**MarketTrust AI** cross-references claims against the SEBI registered entity database "
            "and flags communications that violate SEBI guidelines (e.g., guaranteed returns, "
            "fake registration numbers, unregistered advisory services)."
        )
        return _with_rag_supplement(reply)

    if any(w in msg for w in ["trust score", "score", "rating"]):
        reply = (
            "**Trust Scores** range from 0 to 100:\n\n"
            "- **80-100**: Low risk — communication appears trustworthy\n"
            "- **60-79**: Medium risk — exercise caution, some concerns detected\n"
            "- **40-59**: High risk — significant red flags found\n"
            "- **0-39**: Critical risk — likely fraudulent communication\n\n"
            "The score is calculated from 4 axes:\n"
            "1. **Media Authenticity** — Deepfake detection, image forensics (ELA)\n"
            "2. **Claim Verification** — Cross-referencing claims against databases\n"
            "3. **Source Credibility** — Domain age, SSL, WHOIS, registration checks\n"
            "4. **Evidence Strength** — Quality and consistency of supporting evidence"
        )
        return _with_rag_supplement(reply)

    if any(w in msg for w in ["evidence", "verification", "verify", "how does", "how do"]):
        reply = (
            "**Evidence Verification** in MarketTrust uses multiple strategies:\n\n"
            "1. 🔍 **ChromaDB Knowledge Base** — Semantic search against SEBI fraud patterns\n"
            "2. 🤖 **LLM Reasoning** — AI-powered claim fact-checking via Ollama\n"
            "3. 🏛️ **SEBI Database** — Cross-reference with registered entities\n"
            "4. 🔗 **Domain/URL Checks** — WHOIS, SSL, and Google Safe Browsing\n"
            "5. 🚩 **Red Flag Detection** — Pattern matching against known fraud indicators\n\n"
            "Each evidence item shows whether it *supports* or *contradicts* the claim, "
            "along with a confidence percentage."
        )
        return _with_rag_supplement(reply)

    if any(w in msg for w in ["risk", "critical", "high", "danger", "fraud", "scam", "fake"]):
        reply = (
            "**Risk Levels** indicate the likelihood of fraud:\n\n"
            "- 🟢 **Low**: Communication appears legitimate\n"
            "- 🟡 **Medium**: Some concerns — verify independently\n"
            "- 🟠 **High**: Multiple red flags — exercise extreme caution\n"
            "- 🔴 **Critical**: Strong indicators of fraud — do not engage\n\n"
            "Common fraud red flags MarketTrust detects:\n"
            "- Guaranteed returns or \"zero risk\" promises\n"
            "- Fake SEBI registration numbers\n"
            "- Unregistered advisory via WhatsApp/Telegram\n"
            "- Deepfake videos impersonating market experts\n"
            "- Photoshopped P&L screenshots\n\n"
            "If you encounter a critical-risk communication, consider filing a complaint "
            "at [SEBI SCORES](https://scores.sebi.gov.in/)."
        )
        return _with_rag_supplement(reply)

    if any(w in msg for w in ["deepfake", "video", "image", "photo", "forgery", "photoshop"]):
        reply = (
            "**Media Authenticity Analysis** in MarketTrust:\n\n"
            "- **Video**: Faster Whisper transcription + OCR text extraction + deepfake detection\n"
            "- **Image**: Error Level Analysis (ELA) to detect pixel tampering, font inconsistencies, "
            "and compression artifacts\n"
            "- **Email**: SPF/DKIM authentication, domain age verification, header analysis\n"
            "- **Website**: SSL certificate audit, WHOIS domain age check, content scraping\n\n"
            "A low **Media Authenticity Score** indicates the content has been digitally manipulated."
        )
        return _with_rag_supplement(reply)

    if any(w in msg for w in ["claim", "extract"]):
        reply = (
            "**Claim Extraction** is the process of identifying factual assertions from communications:\n\n"
            "- MarketTrust uses AI (Qwen3 via Ollama) to extract **Subject → Predicate → Object** triples\n"
            "- Claims are categorized: `regulatory`, `financial`, `performance`, `prediction`, `identity`\n"
            "- Each claim gets a **confidence score** and is then verified against multiple evidence sources\n"
            "- Claims mentioning SEBI registration, guaranteed returns, or performance figures "
            "are flagged for priority verification"
        )
        return _with_rag_supplement(reply)

    if any(w in msg for w in ["hello", "hi", "hey", "help"]):
        return (
            "👋 Hello! I'm the **MarketTrust AI Assistant**.\n\n"
            "I can help you with:\n"
            "- 📊 Retrieving **investigation data** from the database\n"
            "- 🔍 Searching **claims and evidence** across all investigations\n"
            "- 📈 Explaining **trust scores** and **risk levels**\n"
            "- 🏛️ Answering questions about **SEBI regulations**\n"
            "- 🚩 Understanding **financial fraud red flags**\n\n"
            "Try asking: *\"Tell me about SEBI regulations\"*, *\"What claims mention guaranteed returns?\"*, "
            "or *\"What is the risk level of the latest investigation?\"*\n\n"
            "💡 *For full conversational AI, start Ollama (`ollama serve`) with the qwen3 model.*"
        )

    # ── Investigation-specific queries: use RAG context ──
    if any(w in msg for w in ["investigation", "recent", "latest", "all", "list", "show", "summary"]):
        if rag_context and retrieved_count > 0:
            clean_context = rag_context.replace("```", "").strip()
            return (
                f"📊 **Retrieved Investigation Summary** ({retrieved_count} sources matched)\n\n"
                f"{clean_context[:1600]}\n\n"
                "💡 *For deeper AI analysis, start Ollama (`ollama serve`).*"
            )

    # ── Generic fallback with RAG context if available ──
    if rag_context and retrieved_count > 0:
        clean_context = rag_context.replace("```", "").strip()
        return (
            f"📋 **Retrieved Market Intelligence** ({retrieved_count} sources matched)\n\n"
            f"{clean_context[:1500]}\n\n"
            "💡 *Start Ollama (`ollama serve`) for full conversational AI responses.*"
        )

    # No RAG context, no topic match
    return (
        "I'm the **MarketTrust AI Assistant** with database access. I can:\n\n"
        "- Search investigations, claims, and evidence\n"
        "- Explain trust scores and risk assessments\n"
        "- Answer SEBI compliance questions\n\n"
        "Try asking about your investigations or any financial regulation topic. "
        "For full AI-powered responses, ensure Ollama is running (`ollama serve`)."
    )


@router.post("/documents/upload")
async def upload_document_for_rag(file: UploadFile = File(...)):
    """Upload a text/CSV/MD file directly into the ChromaDB RAG vector store."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    content_bytes = await file.read()
    try:
        content_text = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read document text: {e}")

    if not content_text.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    from app.chat.rag_indexer import index_raw_document
    indexed_chunks = index_raw_document(file.filename, content_text)

    return {
        "message": f"Successfully indexed '{file.filename}' into RAG collection",
        "filename": file.filename,
        "chunks_indexed": indexed_chunks,
        "status": "success"
    }
