"""
MarketTrust AI — PDF Report Generator.

Generates Trust Passport PDF reports using Jinja2 templates
and WeasyPrint for HTML-to-PDF conversion.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_pdf(investigation) -> bytes:
    """
    Generate a Trust Passport PDF for an investigation.

    Args:
        investigation: Investigation ORM object with loaded relationships.

    Returns:
        PDF file as bytes.
    """
    # Prepare template data
    data = _prepare_report_data(investigation)

    # Render HTML
    html_content = _render_template("passport.html", data)

    # Convert to PDF
    try:
        from weasyprint import HTML

        pdf_bytes = HTML(string=html_content).write_pdf()
        logger.info(f"Generated PDF report for investigation {investigation.id}")
        return pdf_bytes

    except ImportError:
        logger.warning("WeasyPrint not installed, returning HTML as fallback")
        return html_content.encode("utf-8")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        # Fallback: return HTML
        return html_content.encode("utf-8")


def _render_template(template_name: str, data: Dict[str, Any]) -> str:
    """Render a Jinja2 template with the given data."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template(template_name)
    return template.render(**data)


def _prepare_report_data(investigation) -> Dict[str, Any]:
    """Prepare structured data for the report template."""
    passport = investigation.trust_passport
    communications = investigation.communications or []

    # Gather source / raw content metadata
    source_filename = None
    source_url = None
    extracted_text = None
    if communications:
        first_comm = communications[0]
        source_filename = first_comm.original_filename
        source_url = first_comm.url
        extracted_text = first_comm.extracted_text

    # Gather all claims and evidence
    all_claims = []
    for comm in communications:
        for claim in (comm.claims or []):
            claim_data = {
                "subject": claim.subject,
                "predicate": claim.predicate,
                "object": claim.object,
                "confidence": claim.confidence,
                "category": claim.category or "unknown",
                "evidence": [],
            }
            for ev in (claim.evidence or []):
                claim_data["evidence"].append({
                    "source": ev.source,
                    "supports": ev.supports,
                    "confidence": ev.confidence,
                    "explanation": ev.explanation,
                })
            all_claims.append(claim_data)

    # Score color helpers
    def score_color(score: float) -> str:
        if score >= 80:
            return "#10b981"  # Green
        elif score >= 60:
            return "#f59e0b"  # Amber
        elif score >= 40:
            return "#f97316"  # Orange
        else:
            return "#ef4444"  # Red

    def risk_color(level: str) -> str:
        colors = {
            "low": "#10b981",
            "medium": "#f59e0b",
            "high": "#f97316",
            "critical": "#ef4444",
        }
        return colors.get(level, "#6b7280")

    return {
        "investigation": {
            "id": str(investigation.id),
            "title": investigation.title,
            "type": investigation.type or "unknown",
            "created_at": investigation.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            "status": investigation.status,
            "source_filename": source_filename,
            "source_url": source_url,
            "extracted_text": extracted_text,
        },
        "passport": {
            "overall_score": passport.overall_score if passport else 0,
            "risk_level": passport.risk_level if passport else "unknown",
            "recommendation": passport.recommendation if passport else "",
            "media_authenticity": passport.media_authenticity_score if passport else 0,
            "claim_verification": passport.claim_verification_score if passport else 0,
            "source_credibility": passport.source_credibility_score if passport else 0,
            "evidence_strength": passport.evidence_strength_score if passport else 0,
            "details": passport.details_json if passport else {},
        },
        "claims": all_claims,
        "claims_count": len(all_claims),
        "verified_count": sum(
            1
            for c in all_claims
            if any(e["supports"] for e in c["evidence"])
        ),
        "contradicted_count": sum(
            1
            for c in all_claims
            if any(not e["supports"] and e["confidence"] > 0.5 for e in c["evidence"])
        ),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "score_color": score_color,
        "risk_color": risk_color,
    }
