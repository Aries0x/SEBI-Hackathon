"""
MarketTrust AI — Dimension Scorers.

Individual scoring functions for each trust dimension:
- Media Authenticity (25%)
- Claim Verification (30%)
- Source Credibility (25%)
- Evidence Strength (20%)
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


def score_media_authenticity(communications: list) -> float:
    """
    Score media authenticity based on forgery detection,
    metadata consistency, and EXIF analysis.

    Returns score 0-100.
    """
    if not communications:
        return 50.0  # Neutral when no data

    scores: List[float] = []

    for comm in communications:
        metadata = comm.metadata_json or {}
        score = 70.0  # Start with a reasonable baseline

        # Check for forgery analysis results (image pipeline)
        forgery = metadata.get("forgery_analysis", {})
        if forgery:
            if forgery.get("is_suspicious"):
                score -= 30.0
                if forgery.get("suspicious_area_percentage", 0) > 10:
                    score -= 10.0
            else:
                score += 10.0

        # Check EXIF consistency (images)
        exif = metadata.get("exif", {})
        if exif:
            # Has EXIF data — slightly more trustworthy
            score += 5.0
            # Check for editing software indicators
            software = str(exif.get("Software", "")).lower()
            if any(
                tool in software
                for tool in ["photoshop", "gimp", "canva", "paint"]
            ):
                score -= 10.0  # Edited image

        # Check video metadata consistency
        if comm.media_type == "video":
            duration = metadata.get("duration", 0)
            if duration and duration > 0:
                score += 5.0  # Valid video metadata
            if metadata.get("error"):
                score -= 15.0

        # Email auth results
        auth = metadata.get("auth_results", {})
        if auth:
            spf = auth.get("spf", {}).get("status", "unknown")
            dkim = auth.get("dkim", {}).get("status", "unknown")
            if spf == "pass":
                score += 10.0
            elif spf == "fail":
                score -= 20.0
            if dkim == "pass":
                score += 10.0
            elif dkim == "fail":
                score -= 20.0

        # Website SSL
        ssl_info = metadata.get("ssl", {})
        if ssl_info:
            if ssl_info.get("is_valid"):
                score += 10.0
            elif ssl_info.get("has_ssl") is False:
                score -= 15.0

        scores.append(max(0.0, min(100.0, score)))

    return sum(scores) / len(scores)


def score_claim_verification(claims: list, evidence: list) -> float:
    """
    Score claim verification based on the percentage of claims
    supported vs contradicted by evidence.

    Returns score 0-100.
    """
    if not claims:
        return 50.0  # Neutral when no claims

    claim_scores: List[float] = []

    for claim in claims:
        claim_evidence = [
            e for e in evidence if str(e.claim_id) == str(claim.id)
        ]

        if not claim_evidence:
            claim_scores.append(30.0)  # No evidence = low score
            continue

        # Weighted average of evidence
        supporting_weight = sum(
            e.confidence for e in claim_evidence if e.supports
        )
        contradicting_weight = sum(
            e.confidence for e in claim_evidence if not e.supports
        )
        total_weight = supporting_weight + contradicting_weight

        if total_weight == 0:
            claim_scores.append(50.0)
        else:
            # Ratio of supporting evidence
            support_ratio = supporting_weight / total_weight
            claim_scores.append(support_ratio * 100)

    return sum(claim_scores) / len(claim_scores)


def score_source_credibility(communications: list) -> float:
    """
    Score source credibility based on domain age, SEBI registration,
    SPF/DKIM results, SSL validity, etc.

    Returns score 0-100.
    """
    if not communications:
        return 50.0

    scores: List[float] = []

    for comm in communications:
        metadata = comm.metadata_json or {}
        score = 50.0  # Start neutral

        # WHOIS domain age
        whois = metadata.get("whois", {})
        if whois:
            age_days = whois.get("domain_age_days")
            if age_days is not None:
                if age_days < 30:
                    score -= 20.0  # Very new domain
                elif age_days < 90:
                    score -= 10.0  # New domain
                elif age_days < 365:
                    score += 5.0   # Relatively new but established
                elif age_days < 1825:  # 5 years
                    score += 15.0  # Established
                else:
                    score += 20.0  # Well established

            if whois.get("is_new_domain"):
                score -= 10.0

        # SSL certificate
        ssl_info = metadata.get("ssl", {})
        if ssl_info:
            if ssl_info.get("is_valid"):
                score += 10.0
                # Known CAs add trust
                issuer = str(ssl_info.get("issuer", "")).lower()
                trusted_cas = ["let's encrypt", "digicert", "comodo", "geotrust"]
                if any(ca in issuer for ca in trusted_cas):
                    score += 5.0
            elif ssl_info.get("has_ssl") is False:
                score -= 20.0  # No SSL at all

        # Email authentication
        auth = metadata.get("auth_results", {})
        if auth:
            for check in ["spf", "dkim", "dmarc"]:
                status = auth.get(check, {}).get("status", "unknown")
                if status == "pass":
                    score += 8.0
                elif status == "fail":
                    score -= 15.0

        # Render metadata
        render = metadata.get("render", {})
        if render:
            if render.get("redirected"):
                score -= 5.0  # Redirects can be suspicious
            status_code = render.get("status_code")
            if status_code and status_code >= 400:
                score -= 10.0  # Error pages

        scores.append(max(0.0, min(100.0, score)))

    return sum(scores) / len(scores)


def score_evidence_strength(evidence: list) -> float:
    """
    Score overall evidence strength based on number of sources,
    confidence levels, and agreement between sources.

    Returns score 0-100.
    """
    if not evidence:
        return 30.0  # No evidence = low score

    # Count unique sources
    sources = set(e.source for e in evidence)
    source_diversity_bonus = min(len(sources) * 5, 20)

    # Average confidence
    avg_confidence = (
        sum(e.confidence for e in evidence) / len(evidence)
    ) * 100

    # Agreement ratio (what % of evidence agrees)
    if len(evidence) > 1:
        supporting = sum(1 for e in evidence if e.supports)
        majority_direction = supporting > len(evidence) / 2
        agreement = max(supporting, len(evidence) - supporting) / len(evidence)
        agreement_score = agreement * 100
    else:
        agreement_score = 50.0

    # Combine factors
    score = (
        avg_confidence * 0.4
        + agreement_score * 0.3
        + source_diversity_bonus
        + min(len(evidence) * 3, 15)  # More evidence = better (capped)
    )

    return max(0.0, min(100.0, score))
