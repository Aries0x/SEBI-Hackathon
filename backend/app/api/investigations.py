"""
MarketTrust AI — Investigation API Endpoints.

POST /api/investigations              — Create a new investigation
POST /api/investigations/demo/{id}     — Seed a rich demo scenario
POST /api/investigations/{id}/upload  — Upload media file
POST /api/investigations/{id}/url     — Submit a website URL
GET  /api/investigations              — List all investigations
GET  /api/investigations/{id}         — Get investigation details
GET  /api/investigations/{id}/report  — Download Trust Passport PDF
"""

from __future__ import annotations

import logging
import uuid
import concurrent.futures
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.api.schemas import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationSummary,
    UploadResponse,
    WebsiteUpload,
)
from app.database.models import (
    Claim,
    Communication,
    Evidence,
    Investigation,
    TrustPassport,
)
from app.storage import upload_file as minio_upload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["investigations"])
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# ── Media type detection ────────────────────────────────────

MIME_TO_TYPE = {
    "video/mp4": "video",
    "video/avi": "video",
    "video/x-msvideo": "video",
    "video/quicktime": "video",
    "video/x-matroska": "video",
    "video/webm": "video",
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/bmp": "image",
    "image/tiff": "image",
    "message/rfc822": "email",
    "application/octet-stream": None,
}

EXTENSION_TO_TYPE = {
    ".mp4": "video",
    ".avi": "video",
    ".mov": "video",
    ".mkv": "video",
    ".webm": "video",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".bmp": "image",
    ".tiff": "image",
    ".eml": "email",
    ".msg": "email",
}


def detect_media_type(
    filename: str,
    content_type: str,
    file_bytes: bytes = b"",
    default_type: Optional[str] = None,
) -> str:
    """Detect media type from MIME type, extension, magic bytes, or fallback type."""
    # 1. Check known MIME type (excluding generic binary stream)
    if content_type and content_type != "application/octet-stream":
        media_type = MIME_TO_TYPE.get(content_type)
        if media_type:
            return media_type

    # 2. Check file extension
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        media_type = EXTENSION_TO_TYPE.get(ext)
        if media_type:
            return media_type

    # 3. Check magic header bytes
    if file_bytes:
        header = file_bytes[:512]
        # Image magic bytes (JPEG, PNG, GIF, BMP, WEBP)
        if (
            header.startswith(b"\xff\xd8\xff")
            or header.startswith(b"\x89PNG\r\n\x1a\n")
            or header.startswith(b"GIF8")
            or header.startswith(b"BM")
            or b"WEBP" in header[:20]
        ):
            return "image"

        # Video magic bytes (MP4, MKV/WebM, AVI)
        if (
            b"ftyp" in header[:32]
            or header.startswith(b"\x1a\x45\xdf\xa3")
            or (header.startswith(b"RIFF") and b"AVI " in header[:16])
        ):
            return "video"

        # Email magic bytes / headers
        header_lower = header.lower()
        if (
            b"from:" in header_lower
            or b"subject:" in header_lower
            or b"received:" in header_lower
            or b"mime-version:" in header_lower
        ):
            return "email"

    # 4. Fallback to user-selected media type from investigation
    if default_type in ("image", "video", "email", "website"):
        return default_type

    raise ValueError(f"Unsupported file type: {content_type} ({filename})")


# ── POST /api/investigations ────────────────────────────────


@router.post(
    "/investigations",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_investigation(
    body: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new investigation."""
    investigation = Investigation(
        title=body.title,
        type=body.type,
        status="pending",
    )
    db.add(investigation)
    await db.flush()

    result = await db.execute(
        select(Investigation)
        .where(Investigation.id == investigation.id)
        .options(
            selectinload(Investigation.communications),
            selectinload(Investigation.trust_passport),
        )
    )
    inv = result.scalar_one()

    logger.info(f"Created investigation {inv.id}: {inv.title}")
    return inv


# ── POST /api/investigations/demo/{scenario_id} ────────────


@router.post(
    "/investigations/demo/{scenario_id}",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_demo_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Seed a realistic sample investigation for 1-click demo testing."""
    scenarios = {
        "video_deepfake": {
            "title": "🚨 Suspicious YouTube Deepfake: Guaranteed 45% Monthly Return",
            "type": "video",
            "extracted_text": (
                "[TRANSCRIPT]\nWelcome back smart investors! Today I'm revealing an exclusive SEBI-approved algorithm "
                "that guarantees a 45% return every single month with zero risk. Join our private Telegram channel now! "
                "We are SEBI Registered Advisory INZ00099999.\n\n[OCR TEXT]\nGUARANTEED 45% MONTHLY RETURN | 100% RISK FREE | JOIN TELEGRAM @QUANT_TIPS"
            ),
            "claims": [
                {"subject": "Algorithmic Scheme", "predicate": "guarantees monthly return of", "object": "45% profit", "confidence": 0.95, "category": "financial", "supports": False, "exp": "Unrealistic return claim. No regulated investment guarantees 45% monthly profit."},
                {"subject": "Quant Tips Entity", "predicate": "claims SEBI registration as", "object": "INZ00099999", "confidence": 0.90, "category": "regulatory", "supports": False, "exp": "Registration number INZ00099999 is fake and not found in SEBI database."},
                {"subject": "Investment Scheme", "predicate": "promises risk level of", "object": "0% / Risk-Free", "confidence": 0.98, "category": "prediction", "supports": False, "exp": "Red Flag: SEBI strictly prohibits 'risk-free' investment claims."},
            ],
            "media_score": 35.0, "claim_score": 15.0, "source_score": 20.0, "evidence_score": 25.0, "overall": 23.5, "risk": "critical",
            "recommendation": "🚨 CRITICAL RISK: Fraudulent deepfake communication promising illegal guaranteed returns and displaying fake SEBI registration credentials."
        },
        "image_pnl_forgery": {
            "title": "🖼️ Photoshopped Zerodha P&L Profit Screenshot (₹48 Lakhs)",
            "type": "image",
            "extracted_text": (
                "[OCR TEXT]\nZerodha Console - Reports - P&L\nRealized P&L: +₹48,25,400.00 (+340.5%)\n"
                "Trade Date: 12 July 2026\nStatus: Verified Trader\nContact WhatsApp for daily call alerts"
            ),
            "claims": [
                {"subject": "Trader Portfolio", "predicate": "claims realized profit of", "object": "₹48,25,400 (+340%)", "confidence": 0.92, "category": "performance", "supports": False, "exp": "Error Level Analysis (ELA) indicates localized pixel tampering around the profit figure."},
                {"subject": "WhatsApp Service", "predicate": "offers daily stock calls via", "object": "Unregistered WhatsApp", "confidence": 0.88, "category": "regulatory", "supports": False, "exp": "Unregistered tip provision on WhatsApp violates SEBI Investment Adviser Regulations."}
            ],
            "media_score": 28.0, "claim_score": 40.0, "source_score": 30.0, "evidence_score": 35.0, "overall": 33.0, "risk": "critical",
            "recommendation": "🚨 CRITICAL RISK: Digital forgery detected via Error Level Analysis. Font alignment and pixel compression inconsistent with authentic Zerodha P&L exports."
        },
        "email_phishing": {
            "title": "📧 Spoofed SEBI IPO Allotment Email with Fake Attachment",
            "type": "email",
            "extracted_text": (
                "[EMAIL SUBJECT]\nURGENT: SEBI Priority IPO Direct Allotment Confirmation\n\n"
                "[EMAIL FROM]\nallotment-notice@sebi-gov-portal.com\n\n"
                "[EMAIL BODY]\nDear Investor, You have been selected for exclusive direct allotment of Tata Tech IPO shares at a 60% discount. "
                "Pay ₹50,000 via direct UPI to reserve your shares before 5:00 PM today."
            ),
            "claims": [
                {"subject": "SEBI Authority", "predicate": "offers direct IPO share allotment at", "object": "60% Discount", "confidence": 0.96, "category": "regulatory", "supports": False, "exp": "SEBI does not sell or allot IPO shares directly to retail investors."},
                {"subject": "Sender Address", "predicate": "fails SPF/DKIM verification for domain", "object": "sebi-gov-portal.com", "confidence": 0.99, "category": "identity", "supports": False, "exp": "Domain sebi-gov-portal.com was registered 2 days ago and failed SPF & DKIM authentication."}
            ],
            "media_score": 45.0, "claim_score": 20.0, "source_score": 10.0, "evidence_score": 20.0, "overall": 24.5, "risk": "critical",
            "recommendation": "🚨 CRITICAL RISK: High-risk phishing attack impersonating SEBI. Domain age is 2 days and SPF/DKIM authentication checks failed."
        },
        "legitimate_broker": {
            "title": "✅ Legitimate Broker Research Note: ICICI Securities Nifty 50 Outlook",
            "type": "website",
            "extracted_text": (
                "[WEBSITE TITLE]\nICICI Direct - Nifty 50 Market Analysis & Research Note\n\n"
                "[PAGE CONTENT]\nICICI Securities Ltd (SEBI Reg No: INZ000183631). Nifty 50 trades at 24,500 with forward P/E of 21.5x. "
                "Key upside target of 25,200 based on earnings growth projections. Past performance does not guarantee future results. "
                "Read full disclaimers at icicidirect.com."
            ),
            "claims": [
                {"subject": "ICICI Securities Ltd", "predicate": "is registered with SEBI as", "object": "INZ000183631", "confidence": 0.98, "category": "regulatory", "supports": True, "exp": "Verified: INZ000183631 matches official SEBI registered stock broker database."},
                {"subject": "Nifty Target", "predicate": "projects target price of", "object": "25,200 based on 21.5x P/E", "confidence": 0.85, "category": "performance", "supports": True, "exp": "Standard research forecast accompanied by mandatory SEBI risk disclosures."}
            ],
            "media_score": 95.0, "claim_score": 88.0, "source_score": 96.0, "evidence_score": 90.0, "overall": 92.0, "risk": "low",
            "recommendation": "✅ LOW RISK: Verified legitimate financial research note from SEBI-registered broker ICICI Securities Ltd with valid SSL and WHOIS history."
        }
    }

    scen = scenarios.get(scenario_id, scenarios["video_deepfake"])

    # Create investigation
    investigation = Investigation(
        title=scen["title"],
        type=scen["type"],
        status="completed",
    )
    db.add(investigation)
    await db.flush()

    # Create communication
    comm = Communication(
        investigation_id=investigation.id,
        media_type=scen["type"],
        extracted_text=scen["extracted_text"],
        original_filename=f"demo_{scenario_id}.dat",
        processing_status="completed",
        processing_step="Complete",
        metadata_json={
            "is_demo": True,
            "scenario": scenario_id,
            "forgery_analysis": {"is_suspicious": scen["overall"] < 50, "mean_ela_difference": 18.4},
            "whois": {"domain_age_days": 1820 if scen["overall"] > 50 else 2, "registrar": "GoDaddy"},
            "ssl": {"is_valid": True, "issuer": "DigiCert"}
        }
    )
    db.add(comm)
    await db.flush()

    # Create claims & evidence
    for c_data in scen["claims"]:
        claim = Claim(
            communication_id=comm.id,
            subject=c_data["subject"],
            predicate=c_data["predicate"],
            object=c_data["object"],
            confidence=c_data["confidence"],
            category=c_data["category"],
            raw_text=f"{c_data['subject']} {c_data['predicate']} {c_data['object']}"
        )
        db.add(claim)
        await db.flush()

        evidence = Evidence(
            claim_id=claim.id,
            source="sebi_database" if c_data["category"] == "regulatory" else "red_flag_detection",
            supports=c_data["supports"],
            confidence=c_data["confidence"],
            explanation=c_data["exp"],
        )
        db.add(evidence)

    # Create Trust Passport
    passport = TrustPassport(
        investigation_id=investigation.id,
        overall_score=scen["overall"],
        risk_level=scen["risk"],
        recommendation=scen["recommendation"],
        media_authenticity_score=scen["media_score"],
        claim_verification_score=scen["claim_score"],
        source_credibility_score=scen["source_score"],
        evidence_strength_score=scen["evidence_score"],
        details_json={"demo": True, "scenario": scenario_id}
    )
    db.add(passport)
    await db.flush()

    # Query full response
    result = await db.execute(
        select(Investigation)
        .where(Investigation.id == investigation.id)
        .options(
            selectinload(Investigation.communications)
            .selectinload(Communication.claims)
            .selectinload(Claim.evidence),
            selectinload(Investigation.trust_passport),
        )
    )
    inv = result.scalar_one()

    # Index into ChromaDB RAG collection
    try:
        from app.chat.rag_indexer import index_investigation_from_orm
        index_investigation_from_orm(inv)
    except Exception as e:
        logger.warning(f"Failed to auto-index demo scenario into RAG vector db: {e}")

    return inv


# ── POST /api/investigations/{id}/upload ────────────────────


@router.post(
    "/investigations/{investigation_id}/upload",
    response_model=UploadResponse,
)
async def upload_media(
    investigation_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a media file for an existing investigation."""
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    try:
        media_type = detect_media_type(file.filename or "", file.content_type or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    file_data = await file.read()
    object_name = f"{investigation_id}/{uuid.uuid4()}/{file.filename}"
    minio_upload(
        object_name=object_name,
        data=file_data,
        content_type=file.content_type or "application/octet-stream",
    )

    communication = Communication(
        investigation_id=investigation_id,
        file_path=object_name,
        media_type=media_type,
        original_filename=file.filename,
        processing_status="pending",
    )
    db.add(communication)

    investigation.type = media_type
    investigation.status = "processing"
    await db.flush()
    await db.refresh(communication)

    _dispatch_pipeline(communication.id, media_type)

    logger.info(
        f"Uploaded {file.filename} ({media_type}) for investigation {investigation_id}"
    )

    return UploadResponse(
        communication_id=communication.id,
        filename=file.filename or "unknown",
        media_type=media_type,
        status="processing",
        message=f"File uploaded and {media_type} pipeline started.",
    )


# ── POST /api/investigations/{id}/url ──────────────────────


@router.post(
    "/investigations/{investigation_id}/url",
    response_model=UploadResponse,
)
async def submit_url(
    investigation_id: uuid.UUID,
    body: WebsiteUpload,
    db: AsyncSession = Depends(get_db),
):
    """Submit a website URL for investigation."""
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    communication = Communication(
        investigation_id=investigation_id,
        media_type="website",
        url=body.url,
        processing_status="pending",
    )
    db.add(communication)

    investigation.type = "website"
    investigation.status = "processing"
    await db.flush()
    await db.refresh(communication)

    _dispatch_pipeline(communication.id, "website")

    logger.info(
        f"Submitted URL {body.url} for investigation {investigation_id}"
    )

    return UploadResponse(
        communication_id=communication.id,
        filename=body.url,
        media_type="website",
        status="processing",
        message="Website pipeline started.",
    )


# ── GET /api/investigations ────────────────────────────────


@router.get(
    "/investigations",
    response_model=List[InvestigationSummary],
)
async def list_investigations(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all investigations with pagination."""
    result = await db.execute(
        select(Investigation)
        .options(selectinload(Investigation.trust_passport))
        .order_by(Investigation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    investigations = result.scalars().all()

    summaries = []
    for inv in investigations:
        summary = InvestigationSummary(
            id=inv.id,
            title=inv.title,
            status=inv.status,
            type=inv.type,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            trust_score=inv.trust_passport.overall_score
            if inv.trust_passport
            else None,
            risk_level=inv.trust_passport.risk_level
            if inv.trust_passport
            else None,
        )
        summaries.append(summary)

    return summaries


# ── GET /api/investigations/{id} ────────────────────────────


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationResponse,
)
async def get_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full investigation details including claims and evidence."""
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
    investigation = result.scalar_one_or_none()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return investigation


# ── GET /api/investigations/{id}/report ─────────────────────


@router.get("/investigations/{investigation_id}/report")
async def download_report(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download the Trust Passport as a PDF report."""
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
    investigation = result.scalar_one_or_none()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if not investigation.trust_passport:
        raise HTTPException(
            status_code=404,
            detail="Trust Passport not yet generated. Investigation may still be processing.",
        )

    from app.reports.generator import generate_pdf

    pdf_bytes = generate_pdf(investigation)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="trust_passport_{investigation_id}.pdf"'
            )
        },
    )


@router.delete("/investigations/{investigation_id}")
async def delete_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an investigation and its associated communications, claims, evidence, and trust passport."""
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    await db.delete(investigation)
    await db.commit()
    return {"message": "Investigation deleted successfully"}


# ── Pipeline dispatch helper with thread fallback ───────────


def is_redis_online() -> bool:
    """Check if the Redis broker is online."""
    import socket
    from urllib.parse import urlparse
    from app.config import settings
    try:
        url = urlparse(settings.redis_url)
        host = url.hostname or "localhost"
        port = url.port or 6379
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except Exception:
        return False


def _dispatch_pipeline(communication_id: uuid.UUID, media_type: str) -> None:
    """Dispatch pipeline via Celery if available, or ThreadPoolExecutor fallback."""
    comm_id_str = str(communication_id)

    def _run_task_func():
        try:
            if media_type == "video":
                from app.video.tasks import process_video
                process_video(comm_id_str)
            elif media_type == "image":
                from app.image.tasks import process_image
                process_image(comm_id_str)
            elif media_type == "email":
                from app.email.tasks import process_email
                process_email(comm_id_str)
            elif media_type == "website":
                from app.website.tasks import process_website
                process_website(comm_id_str)
        except Exception as e:
            logger.exception(f"Background thread execution failed for {media_type} task: {e}")
            try:
                from app.database.connection import get_sync_session
                from app.database.models import Communication, Investigation
                session = get_sync_session()
                comm = session.get(Communication, communication_id)
                if comm:
                    comm.processing_status = "failed"
                    comm.processing_step = f"Critical Error: {str(e)[:200]}"
                    inv = session.get(Investigation, comm.investigation_id)
                    if inv:
                        inv.status = "failed"
                session.commit()
                session.close()
            except Exception as db_err:
                logger.error(f"Failed to mark background thread task as failed: {db_err}")


    # Force local thread execution if Redis is not online
    if not is_redis_online():
        logger.warning(
            f"Redis broker offline. Running {media_type} pipeline in background thread."
        )
        executor.submit(_run_task_func)
        return

    try:
        if media_type == "video":
            from app.video.tasks import process_video
            process_video.delay(comm_id_str)
        elif media_type == "image":
            from app.image.tasks import process_image
            process_image.delay(comm_id_str)
        elif media_type == "email":
            from app.email.tasks import process_email
            process_email.delay(comm_id_str)
        elif media_type == "website":
            from app.website.tasks import process_website
            process_website.delay(comm_id_str)
        logger.info(f"Dispatched {media_type} task to Celery queue")
    except Exception as e:
        logger.warning(
            f"Celery dispatch failed ({e}). Running {media_type} pipeline in background thread."
        )
        executor.submit(_run_task_func)

