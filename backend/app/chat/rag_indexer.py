"""
MarketTrust AI — RAG Indexing Engine.

Automatically indexes investigation data (extracted text, claims, evidence,
trust passports) into ChromaDB for semantic retrieval by the chatbot.

Collection: ``investigations_rag``

Each document carries rich metadata so the chat retrieval layer can:
- Link results back to specific investigations / claims / evidence
- Filter by risk level, document type, or investigation ID
- Render clickable source citations in the frontend
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

# Name of the ChromaDB collection used for chatbot RAG
RAG_COLLECTION = "investigations_rag"

# Maximum chunk size for text splitting (characters)
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


# ── Public API ──────────────────────────────────────────────


def ensure_rag_collection() -> None:
    """Create the RAG collection in ChromaDB if it does not exist."""
    try:
        client = _get_chroma_client()
        if client is None:
            return
        client.get_or_create_collection(
            name=RAG_COLLECTION,
            metadata={"description": "Investigation data for RAG chatbot retrieval"},
        )
        logger.info("ChromaDB RAG collection '%s' ready.", RAG_COLLECTION)
    except Exception as e:
        logger.warning("Could not initialise ChromaDB RAG collection: %s", e)


def index_investigation(
    investigation_id: str,
    title: str,
    inv_type: str,
    status: str,
    created_at: Optional[str] = None,
    communications: Optional[List[Dict[str, Any]]] = None,
    trust_passport: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Index all data from a completed investigation into ChromaDB.

    Parameters
    ----------
    investigation_id : str
        UUID of the investigation.
    title : str
        Title of the investigation.
    inv_type : str
        Media type (video | image | email | website).
    status : str
        Investigation status.
    created_at : str, optional
        ISO timestamp of creation.
    communications : list, optional
        List of communication dicts, each containing ``extracted_text``,
        ``claims`` (list of claim dicts with ``evidence`` sub-list).
    trust_passport : dict, optional
        Trust passport data with scores and recommendation.

    Returns
    -------
    int
        Number of documents indexed.
    """
    client = _get_chroma_client()
    if client is None:
        return 0

    try:
        collection = client.get_or_create_collection(name=RAG_COLLECTION)
    except Exception as e:
        logger.warning("ChromaDB collection access failed: %s", e)
        return 0

    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    base_meta = {
        "investigation_id": investigation_id,
        "investigation_title": title,
        "investigation_type": inv_type or "unknown",
        "investigation_status": status,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }

    # Add trust passport scores to base metadata when available
    if trust_passport:
        base_meta["trust_score"] = trust_passport.get("overall_score", 0)
        base_meta["risk_level"] = trust_passport.get("risk_level", "unknown")

    # ── Index extracted text (chunked) ──────────────────────
    for comm in (communications or []):
        text = comm.get("extracted_text") or ""
        if not text.strip():
            continue

        chunks = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        for i, chunk in enumerate(chunks):
            doc_id = _make_id(investigation_id, "text", str(i))
            documents.append(chunk)
            metadatas.append({
                **base_meta,
                "document_type": "extracted_text",
                "chunk_index": i,
                "total_chunks": len(chunks),
            })
            ids.append(doc_id)

    # ── Index claims ────────────────────────────────────────
    for comm in (communications or []):
        for claim in (comm.get("claims") or []):
            claim_text = (
                f"Claim: {claim.get('subject', '')} {claim.get('predicate', '')} "
                f"{claim.get('object', '')}. "
                f"Category: {claim.get('category', 'general')}. "
                f"Confidence: {claim.get('confidence', 0):.0%}."
            )
            raw = claim.get("raw_text") or ""
            if raw:
                claim_text += f" Original text: {raw[:200]}"

            doc_id = _make_id(
                investigation_id, "claim", str(claim.get("id", ""))
            )
            documents.append(claim_text)
            metadatas.append({
                **base_meta,
                "document_type": "claim",
                "claim_id": str(claim.get("id", "")),
                "claim_category": claim.get("category", "general"),
                "claim_confidence": claim.get("confidence", 0),
            })
            ids.append(doc_id)

            # ── Index evidence for this claim ───────────────
            for ev in (claim.get("evidence") or []):
                explanation = ev.get("explanation") or ""
                if not explanation.strip():
                    continue

                verdict = "supports" if ev.get("supports") else "contradicts"
                ev_text = (
                    f"Evidence ({verdict}, confidence {ev.get('confidence', 0):.0%}) "
                    f"via {ev.get('source', 'unknown')}: {explanation}"
                )

                doc_id = _make_id(
                    investigation_id, "evidence", str(ev.get("id", ""))
                )
                documents.append(ev_text)
                metadatas.append({
                    **base_meta,
                    "document_type": "evidence",
                    "evidence_id": str(ev.get("id", "")),
                    "evidence_source": ev.get("source", "unknown"),
                    "evidence_supports": ev.get("supports", False),
                    "evidence_confidence": ev.get("confidence", 0),
                    "claim_id": str(claim.get("id", "")),
                })
                ids.append(doc_id)

    # ── Index trust passport ────────────────────────────────
    if trust_passport:
        recommendation = trust_passport.get("recommendation") or ""
        passport_text = (
            f"Trust Passport for investigation \"{title}\": "
            f"Overall score {trust_passport.get('overall_score', 0)}/100, "
            f"Risk level: {trust_passport.get('risk_level', 'unknown')}. "
            f"Media Authenticity: {trust_passport.get('media_authenticity_score', 0)}/100, "
            f"Claim Verification: {trust_passport.get('claim_verification_score', 0)}/100, "
            f"Source Credibility: {trust_passport.get('source_credibility_score', 0)}/100, "
            f"Evidence Strength: {trust_passport.get('evidence_strength_score', 0)}/100. "
            f"Recommendation: {recommendation}"
        )

        doc_id = _make_id(investigation_id, "passport", "0")
        documents.append(passport_text)
        metadatas.append({
            **base_meta,
            "document_type": "trust_passport",
        })
        ids.append(doc_id)

    # ── Upsert to ChromaDB ──────────────────────────────────
    if not documents:
        return 0

    try:
        # Upsert in batches of 40 to avoid oversized requests
        batch_size = 40
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            collection.upsert(
                documents=documents[start:end],
                metadatas=metadatas[start:end],
                ids=ids[start:end],
            )
        logger.info(
            "Indexed %d documents for investigation %s into ChromaDB.",
            len(documents),
            investigation_id,
        )
        return len(documents)
    except Exception as e:
        logger.warning("ChromaDB upsert failed: %s", e)
        return 0


def index_raw_document(filename: str, content: str) -> int:
    """Index an uploaded text/document directly into ChromaDB RAG store."""
    client = _get_chroma_client()
    if client is None:
        return 0

    try:
        collection = client.get_or_create_collection(name=RAG_COLLECTION)
    except Exception as e:
        logger.warning("ChromaDB collection access failed: %s", e)
        return 0

    chunks = _chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
    if not chunks:
        return 0

    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    doc_id_base = hashlib.sha256(f"upload:{filename}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16]

    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        ids.append(f"doc_{doc_id_base}_{i}")
        metadatas.append({
            "investigation_id": f"upload_{doc_id_base}",
            "investigation_title": f"Document: {filename}",
            "investigation_type": "document",
            "document_type": "uploaded_document",
            "filename": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    try:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        logger.info("Indexed raw document '%s' (%d chunks) into ChromaDB.", filename, len(chunks))
        return len(chunks)
    except Exception as e:
        logger.warning("ChromaDB document upsert failed: %s", e)
        return 0


def search_rag(
    query: str,
    n_results: int = 8,
    investigation_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Semantic search across the RAG collection.

    Parameters
    ----------
    query : str
        The user's question / search text.
    n_results : int
        Number of results to return.
    investigation_id : str, optional
        If provided, restrict results to a specific investigation.

    Returns
    -------
    list of dict
        Each dict has: ``document``, ``metadata``, ``distance``, ``confidence``.
    """
    client = _get_chroma_client()
    if client is None:
        return []

    try:
        collection = client.get_collection(name=RAG_COLLECTION)
    except Exception:
        logger.debug("RAG collection '%s' not found.", RAG_COLLECTION)
        return []

    where_filter = None
    if investigation_id:
        where_filter = {"investigation_id": investigation_id}

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )
    except Exception as e:
        logger.warning("ChromaDB query failed: %s", e)
        return []

    hits: List[Dict[str, Any]] = []
    if not results or not results.get("documents") or not results["documents"][0]:
        return hits

    for i, doc in enumerate(results["documents"][0]):
        distance = (
            results["distances"][0][i]
            if results.get("distances") and results["distances"][0]
            else 1.0
        )
        metadata = (
            results["metadatas"][0][i]
            if results.get("metadatas") and results["metadatas"][0]
            else {}
        )
        confidence = max(0.0, min(1.0, 1.0 - distance / 2.0))

        if confidence > 0.25:  # Only include reasonably relevant results
            hits.append({
                "document": doc,
                "metadata": metadata,
                "distance": distance,
                "confidence": round(confidence, 3),
            })

    return hits


# ── Helpers ─────────────────────────────────────────────────


def _get_chroma_client():
    """Get a ChromaDB HTTP client, or None if unavailable."""
    try:
        import chromadb

        return chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    except ImportError:
        logger.debug("chromadb package not available")
        return None
    except Exception as e:
        logger.warning("ChromaDB client creation failed: %s", e)
        return None


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split *text* into overlapping chunks, preferring sentence boundaries.

    Returns at least one chunk even for short texts.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    # Split on sentence boundaries for cleaner chunks
    sentences = re.split(r"(?<=[.!?\n])\s+", text)
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > chunk_size and current:
            chunks.append(current.strip())
            # Keep overlap from end of previous chunk
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = overlap_text + " " + sentence
        else:
            current = (current + " " + sentence).strip()

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text[:chunk_size]]


def _make_id(investigation_id: str, doc_type: str, suffix: str) -> str:
    """Generate a deterministic, unique ChromaDB document ID."""
    raw = f"{investigation_id}:{doc_type}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def index_investigation_from_orm(investigation) -> int:
    """
    Convenience wrapper that accepts an ORM Investigation object
    (with eagerly loaded relationships) and indexes it.

    Designed to be called from the API layer after investigation completion.
    """
    comms_data = []
    for comm in (investigation.communications or []):
        claims_data = []
        for claim in (comm.claims or []):
            evidence_data = []
            for ev in (claim.evidence or []):
                evidence_data.append({
                    "id": str(ev.id),
                    "source": ev.source,
                    "supports": ev.supports,
                    "confidence": ev.confidence,
                    "explanation": ev.explanation,
                })
            claims_data.append({
                "id": str(claim.id),
                "subject": claim.subject,
                "predicate": claim.predicate,
                "object": claim.object,
                "confidence": claim.confidence,
                "raw_text": claim.raw_text,
                "category": claim.category,
                "evidence": evidence_data,
            })
        comms_data.append({
            "extracted_text": comm.extracted_text,
            "claims": claims_data,
        })

    passport_data = None
    if investigation.trust_passport:
        tp = investigation.trust_passport
        passport_data = {
            "overall_score": tp.overall_score,
            "risk_level": tp.risk_level,
            "recommendation": tp.recommendation,
            "media_authenticity_score": tp.media_authenticity_score,
            "claim_verification_score": tp.claim_verification_score,
            "source_credibility_score": tp.source_credibility_score,
            "evidence_strength_score": tp.evidence_strength_score,
        }

    return index_investigation(
        investigation_id=str(investigation.id),
        title=investigation.title,
        inv_type=investigation.type or "unknown",
        status=investigation.status,
        created_at=investigation.created_at.isoformat()
        if investigation.created_at
        else None,
        communications=comms_data,
        trust_passport=passport_data,
    )
