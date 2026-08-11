"""
MarketTrust AI — Trust Engine.

Calculates the overall Trust Passport score from 4 weighted dimensions:
Media Authenticity, Claim Verification, Source Credibility, Evidence Strength.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.trust.scorer import (
    score_claim_verification,
    score_evidence_strength,
    score_media_authenticity,
    score_source_credibility,
)

logger = logging.getLogger(__name__)

# ── Weight Configuration ────────────────────────────────────
WEIGHTS = {
    "media_authenticity": 0.25,
    "claim_verification": 0.30,
    "source_credibility": 0.25,
    "evidence_strength": 0.20,
}

# ── Risk Level Thresholds ───────────────────────────────────
RISK_THRESHOLDS = [
    (80, "low"),
    (60, "medium"),
    (40, "high"),
    (0, "critical"),
]


def calculate_trust(session, investigation_id: str) -> Optional[dict]:
    """
    Calculate and persist the Trust Passport for an investigation.

    Args:
        session: SQLAlchemy session.
        investigation_id: UUID of the investigation.

    Returns:
        Dict with trust passport details, or None on failure.
    """
    from app.database.models import (
        Claim,
        Communication,
        Evidence,
        Investigation,
        TrustPassport,
    )

    import uuid
    inv_uuid = uuid.UUID(investigation_id) if isinstance(investigation_id, str) else investigation_id

    investigation = session.get(Investigation, inv_uuid)
    if not investigation:
        logger.error(f"Investigation {investigation_id} not found")
        return None

    # Gather all communications, claims, and evidence
    communications = (
        session.query(Communication)
        .filter(Communication.investigation_id == inv_uuid)
        .all()
    )

    all_claims = []
    all_evidence = []
    for comm in communications:
        claims = (
            session.query(Claim)
            .filter(Claim.communication_id == comm.id)
            .all()
        )
        all_claims.extend(claims)
        for claim in claims:
            evidence_items = (
                session.query(Evidence)
                .filter(Evidence.claim_id == claim.id)
                .all()
            )
            all_evidence.extend(evidence_items)

    # ── Calculate dimension scores ──────────────────────────
    media_score = score_media_authenticity(communications)
    claim_score = score_claim_verification(all_claims, all_evidence)
    source_score = score_source_credibility(communications)
    evidence_score = score_evidence_strength(all_evidence)

    # ── Weighted overall score ──────────────────────────────
    overall_score = (
        media_score * WEIGHTS["media_authenticity"]
        + claim_score * WEIGHTS["claim_verification"]
        + source_score * WEIGHTS["source_credibility"]
        + evidence_score * WEIGHTS["evidence_strength"]
    )

    # ── Risk level ──────────────────────────────────────────
    risk_level = "unknown"
    for threshold, level in RISK_THRESHOLDS:
        if overall_score >= threshold:
            risk_level = level
            break

    # ── Generate recommendation ─────────────────────────────
    recommendation = _generate_recommendation(
        overall_score, risk_level, all_claims, all_evidence, communications
    )

    # ── Build details breakdown ─────────────────────────────
    details = {
        "dimensions": {
            "media_authenticity": {
                "score": round(media_score, 1),
                "weight": WEIGHTS["media_authenticity"],
                "weighted": round(media_score * WEIGHTS["media_authenticity"], 1),
            },
            "claim_verification": {
                "score": round(claim_score, 1),
                "weight": WEIGHTS["claim_verification"],
                "weighted": round(claim_score * WEIGHTS["claim_verification"], 1),
            },
            "source_credibility": {
                "score": round(source_score, 1),
                "weight": WEIGHTS["source_credibility"],
                "weighted": round(source_score * WEIGHTS["source_credibility"], 1),
            },
            "evidence_strength": {
                "score": round(evidence_score, 1),
                "weight": WEIGHTS["evidence_strength"],
                "weighted": round(evidence_score * WEIGHTS["evidence_strength"], 1),
            },
        },
        "claims_count": len(all_claims),
        "evidence_count": len(all_evidence),
        "verified_claims": sum(
            1
            for c in all_claims
            if any(
                e.supports and e.confidence > 0.5
                for e in all_evidence
                if str(e.claim_id) == str(c.id)
            )
        ),
        "contradicted_claims": sum(
            1
            for c in all_claims
            if any(
                not e.supports and e.confidence > 0.5
                for e in all_evidence
                if str(e.claim_id) == str(c.id)
            )
        ),
    }

    # ── Persist Trust Passport ──────────────────────────────
    existing = (
        session.query(TrustPassport)
        .filter(TrustPassport.investigation_id == inv_uuid)
        .first()
    )

    if existing:
        existing.overall_score = round(overall_score, 1)
        existing.risk_level = risk_level
        existing.recommendation = recommendation
        existing.media_authenticity_score = round(media_score, 1)
        existing.claim_verification_score = round(claim_score, 1)
        existing.source_credibility_score = round(source_score, 1)
        existing.evidence_strength_score = round(evidence_score, 1)
        existing.details_json = details
    else:
        passport = TrustPassport(
            investigation_id=inv_uuid,
            overall_score=round(overall_score, 1),
            risk_level=risk_level,
            recommendation=recommendation,
            media_authenticity_score=round(media_score, 1),
            claim_verification_score=round(claim_score, 1),
            source_credibility_score=round(source_score, 1),
            evidence_strength_score=round(evidence_score, 1),
            details_json=details,
        )
        session.add(passport)

    session.flush()

    logger.info(
        f"Trust Passport for {investigation_id}: "
        f"score={overall_score:.1f}, risk={risk_level}"
    )

    # Auto-index into ChromaDB RAG collection
    try:
        from app.chat.rag_indexer import index_investigation_from_orm
        index_investigation_from_orm(investigation)
    except Exception as e:
        logger.warning(f"Failed to auto-index investigation {investigation_id} into RAG vector db: {e}")

    return {
        "overall_score": round(overall_score, 1),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "details": details,
    }


def _generate_recommendation(
    score: float,
    risk_level: str,
    claims: list,
    evidence: list,
    communications: list,
) -> str:
    """Generate a human-readable recommendation based on the trust assessment."""
    parts = []

    if risk_level == "critical":
        parts.append(
            "⚠️ CRITICAL RISK: This communication shows strong indicators of "
            "potential fraud or misleading information. Do NOT act on any "
            "financial advice or claims made in this communication."
        )
    elif risk_level == "high":
        parts.append(
            "⚠️ HIGH RISK: This communication contains several unverified or "
            "contradicted claims. Exercise extreme caution and independently "
            "verify all claims before making any financial decisions."
        )
    elif risk_level == "medium":
        parts.append(
            "⚡ MODERATE RISK: Some claims in this communication could not be "
            "fully verified. Independently verify key claims, especially those "
            "related to returns or credentials, before proceeding."
        )
    else:
        parts.append(
            "✅ LOW RISK: Claims in this communication are largely supported by "
            "available evidence. Standard due diligence is still recommended "
            "before making financial decisions."
        )

    # Add claim statistics
    verified = sum(
        1
        for c in claims
        if any(
            e.supports and e.confidence > 0.5
            for e in evidence
            if str(e.claim_id) == str(c.id)
        )
    )
    contradicted = sum(
        1
        for c in claims
        if any(
            not e.supports and e.confidence > 0.5
            for e in evidence
            if str(e.claim_id) == str(c.id)
        )
    )
    total = len(claims)

    if total > 0:
        parts.append(
            f"Of {total} claims extracted, {verified} were supported by evidence "
            f"and {contradicted} were contradicted."
        )

    # Check for specific red flags in evidence
    red_flags = [
        e.explanation
        for e in evidence
        if not e.supports and e.source == "red_flag_detection"
    ]
    if red_flags:
        parts.append(
            f"Red flags detected: {'; '.join(red_flags[:3])}"
        )

    return " ".join(parts)
