"""
MarketTrust AI — Website Pipeline Celery Task.

Orchestrates: render → extract → screenshot → WHOIS → SSL → claim extraction
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_db_session():
    from app.database.connection import get_sync_session
    return get_sync_session()



@celery_app.task(bind=True, name="app.website.tasks.process_website")
def process_website(self, communication_id: str) -> dict:
    """Full website processing pipeline."""
    session = _get_db_session()

    try:
        import uuid
        from app.database.models import Claim, Communication, Investigation

        comm_uuid = uuid.UUID(communication_id) if isinstance(communication_id, str) else communication_id
        comm = session.get(Communication, comm_uuid)
        if not comm:
            return {"error": "Communication not found"}

        investigation = session.get(Investigation, comm.investigation_id)
        url = comm.url
        if not url:
            return {"error": "No URL provided"}

        with tempfile.TemporaryDirectory() as tmpdir:
            # ── Render Page ─────────────────────────────────
            _update_status(session, comm, "extracting", "Rendering website...")
            from app.website.scraper import render_page

            screenshot_path = str(Path(tmpdir) / "screenshot.png")
            render_result = render_page(url, screenshot_path)

            # ── Extract Text ────────────────────────────────
            _update_status(session, comm, "extracting", "Extracting content...")
            from app.website.scraper import extract_html

            page_text = render_result.get("text", "")
            if not page_text and render_result.get("html"):
                page_text = extract_html(render_result["html"])

            # ── WHOIS Check ─────────────────────────────────
            _update_status(session, comm, "extracting", "Checking domain WHOIS...")
            from app.website.scraper import check_whois

            whois_result = check_whois(url)

            # ── SSL Check ───────────────────────────────────
            _update_status(session, comm, "extracting", "Checking SSL certificate...")
            from app.website.scraper import check_ssl

            ssl_result = check_ssl(url)

            # ── Combine metadata ────────────────────────────
            metadata = {
                "render": {
                    "title": render_result.get("title"),
                    "final_url": render_result.get("final_url"),
                    "status_code": render_result.get("status_code"),
                    "redirected": render_result.get("redirected"),
                    "links_count": len(render_result.get("links", [])),
                },
                "whois": whois_result,
                "ssl": ssl_result,
                "meta_tags": render_result.get("meta_tags", []),
            }

            extracted_text = (
                f"[WEBSITE TITLE]\n{render_result.get('title', '')}\n\n"
                f"[WEBSITE URL]\n{url}\n\n"
                f"[PAGE CONTENT]\n{page_text[:10000]}\n\n"
                f"[DOMAIN INFO]\n"
                f"Registrar: {whois_result.get('registrar', 'Unknown')}\n"
                f"Domain Age: {whois_result.get('domain_age_days', 'Unknown')} days\n"
                f"SSL Valid: {ssl_result.get('is_valid', 'Unknown')}\n"
            )

            comm.extracted_text = extracted_text
            comm.metadata_json = metadata

            # ── Claim Extraction ────────────────────────────
            _update_status(session, comm, "analyzing", "Extracting claims...")
            from app.claims.extractor import extract_claims

            claims = extract_claims(extracted_text)
            _save_claims(session, comm, claims)

            # ── Evidence Verification ───────────────────────
            _update_status(session, comm, "analyzing", "Verifying evidence...")
            from app.evidence.verifier import verify_all_claims

            verify_all_claims(session, comm.id)

            # ── Trust Score ─────────────────────────────────
            _update_status(session, comm, "analyzing", "Calculating trust score...")
            from app.trust.engine import calculate_trust

            calculate_trust(session, str(comm.investigation_id))

            # ── Done ────────────────────────────────────────
            comm.processing_status = "completed"
            comm.processing_step = "Complete"
            if investigation:
                investigation.status = "completed"
            session.commit()

            return {
                "status": "completed",
                "claims_count": len(claims),
                "page_title": render_result.get("title"),
                "domain_age_days": whois_result.get("domain_age_days"),
                "ssl_valid": ssl_result.get("is_valid"),
            }

    except Exception as e:
        logger.error(f"Website pipeline failed for {communication_id}: {e}")
        _mark_failed(session, communication_id, str(e))
        return {"error": str(e)}
    finally:
        session.close()


def _update_status(session, comm, status, step):
    comm.processing_status = status
    comm.processing_step = step
    session.commit()


def _mark_failed(session, communication_id, error):
    try:
        import uuid
        from app.database.models import Communication, Investigation

        comm_uuid = uuid.UUID(communication_id) if isinstance(communication_id, str) else communication_id
        comm = session.get(Communication, comm_uuid)
        if comm:
            comm.processing_status = "failed"
            comm.processing_step = f"Error: {error[:200]}"
            inv = session.get(Investigation, comm.investigation_id)
            if inv:
                inv.status = "failed"
            session.commit()
    except Exception:
        session.rollback()


def _save_claims(session, comm, claims):
    from app.database.models import Claim

    for c in claims:
        session.add(Claim(
            communication_id=comm.id,
            subject=c.get("subject", ""),
            predicate=c.get("predicate", ""),
            object=c.get("object", ""),
            confidence=c.get("confidence", 0.0),
            raw_text=c.get("raw_text", ""),
            category=c.get("category"),
        ))

    # Add default website technical & safety claims
    domain_name = comm.url or "Website"
    from urllib.parse import urlparse
    domain_label = urlparse(domain_name).netloc or domain_name

    session.add(Claim(
        communication_id=comm.id,
        subject=domain_label,
        predicate="has domain registration with",
        object="Domain Registrar",
        confidence=1.0,
        raw_text="WHOIS domain registration lookup",
        category="regulatory"
    ))
    session.add(Claim(
        communication_id=comm.id,
        subject=domain_label,
        predicate="uses active SSL certificate",
        object="SSL Certificate",
        confidence=1.0,
        raw_text="SSL handshake verification",
        category="technical"
    ))
    session.add(Claim(
        communication_id=comm.id,
        subject=domain_label,
        predicate="is clean from threat warning lists",
        object="Clean Status",
        confidence=1.0,
        raw_text="Threat database verification",
        category="security"
    ))

    session.flush()
