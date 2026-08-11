"""
MarketTrust AI — Email Pipeline Celery Task.

Orchestrates: parse → auth check → body → URLs → claim extraction
"""

from __future__ import annotations

import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_db_session():
    from app.database.connection import get_sync_session
    return get_sync_session()



@celery_app.task(bind=True, name="app.email.tasks.process_email")
def process_email(self, communication_id: str) -> dict:
    """Full email processing pipeline."""
    session = _get_db_session()

    try:
        from app.database.models import Claim, Communication, Investigation
        from app.storage import download_file
        import uuid

        comm_uuid = uuid.UUID(communication_id) if isinstance(communication_id, str) else communication_id
        comm = session.get(Communication, comm_uuid)
        if not comm:
            return {"error": "Communication not found"}

        investigation = session.get(Investigation, comm.investigation_id)

        # ── Download .eml ───────────────────────────────────
        _update_status(session, comm, "extracting", "Downloading email...")
        eml_content = download_file(comm.file_path)

        # ── Parse ───────────────────────────────────────────
        _update_status(session, comm, "extracting", "Parsing email...")
        from app.email.parser import parse_eml

        parsed = parse_eml(eml_content)

        # ── Auth Checks ─────────────────────────────────────
        _update_status(session, comm, "extracting", "Checking authentication...")
        from app.email.parser import check_auth

        auth_results = check_auth(eml_content)

        # ── Combine data ────────────────────────────────────
        metadata = {
            "headers": parsed["headers"],
            "auth_headers": parsed["auth_headers"],
            "auth_results": auth_results,
            "urls": parsed["urls"],
            "attachments": parsed["attachments"],
        }

        body_text = parsed["body"]["text"]
        extracted_text = (
            f"[EMAIL SUBJECT]\n{parsed['headers'].get('subject', '')}\n\n"
            f"[EMAIL FROM]\n{parsed['headers'].get('from', '')}\n\n"
            f"[EMAIL BODY]\n{body_text}\n\n"
            f"[URLS FOUND]\n" + "\n".join(parsed["urls"])
        )

        comm.extracted_text = extracted_text
        comm.metadata_json = metadata

        # ── Claim Extraction ────────────────────────────────
        _update_status(session, comm, "analyzing", "Extracting claims...")
        from app.claims.extractor import extract_claims

        claims = extract_claims(extracted_text)
        _save_claims(session, comm, claims)

        # ── Evidence Verification ───────────────────────────
        _update_status(session, comm, "analyzing", "Verifying evidence...")
        from app.evidence.verifier import verify_all_claims

        verify_all_claims(session, comm.id)

        # ── Trust Score ─────────────────────────────────────
        _update_status(session, comm, "analyzing", "Calculating trust score...")
        from app.trust.engine import calculate_trust

        calculate_trust(session, str(comm.investigation_id))

        # ── Done ────────────────────────────────────────────
        comm.processing_status = "completed"
        comm.processing_step = "Complete"
        if investigation:
            investigation.status = "completed"
        session.commit()

        return {
            "status": "completed",
            "claims_count": len(claims),
            "urls_found": len(parsed["urls"]),
            "spf_status": auth_results.get("spf", {}).get("status"),
            "dkim_status": auth_results.get("dkim", {}).get("status"),
        }

    except Exception as e:
        logger.error(f"Email pipeline failed for {communication_id}: {e}")
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

    # Add default email technical validation claims
    sender = comm.original_filename or "Email Sender"
    session.add(Claim(
        communication_id=comm.id,
        subject=sender,
        predicate="is authenticated via SPF validation",
        object="SPF Alignment",
        confidence=1.0,
        raw_text="SPF record verification check",
        category="regulatory"
    ))
    session.add(Claim(
        communication_id=comm.id,
        subject=sender,
        predicate="carries a valid DKIM digital signature",
        object="DKIM Signature",
        confidence=1.0,
        raw_text="DKIM cryptographic signature verification",
        category="technical"
    ))
    session.add(Claim(
        communication_id=comm.id,
        subject=sender,
        predicate="is not blacklisted in anti-spam threat feeds",
        object="Threat Status",
        confidence=1.0,
        raw_text="Threat database verification",
        category="security"
    ))

    session.flush()
