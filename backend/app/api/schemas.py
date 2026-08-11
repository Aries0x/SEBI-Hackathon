"""
MarketTrust AI — Pydantic Request/Response Schemas.

Defines all API data transfer objects for the investigations endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Request Schemas ─────────────────────────────────────────


class InvestigationCreate(BaseModel):
    """Request body for creating a new investigation."""

    title: str = Field(
        ..., min_length=1, max_length=500, description="Title of the investigation"
    )
    type: Optional[str] = Field(
        None,
        pattern="^(video|image|email|website)$",
        description="Type of media being investigated",
    )


class WebsiteUpload(BaseModel):
    """Request body for submitting a website URL for investigation."""

    url: str = Field(..., min_length=1, max_length=2000, description="Website URL")


# ── Response Schemas ────────────────────────────────────────


class EvidenceResponse(BaseModel):
    """Evidence gathered for a single claim."""

    id: uuid.UUID
    source: str
    source_url: Optional[str] = None
    supports: bool
    confidence: float
    explanation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimResponse(BaseModel):
    """A claim extracted from a communication."""

    id: uuid.UUID
    subject: str
    predicate: str
    object: str
    confidence: float
    raw_text: Optional[str] = None
    category: Optional[str] = None
    evidence: List[EvidenceResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class CommunicationResponse(BaseModel):
    """A communication (media file) within an investigation."""

    id: uuid.UUID
    media_type: str
    original_filename: Optional[str] = None
    url: Optional[str] = None
    processing_status: str
    processing_step: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata_json: Optional[dict] = None
    claims: List[ClaimResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TrustPassportResponse(BaseModel):
    """The trust passport / final assessment."""

    id: uuid.UUID
    overall_score: float
    risk_level: str
    recommendation: str
    media_authenticity_score: float
    claim_verification_score: float
    source_credibility_score: float
    evidence_strength_score: float
    details_json: Optional[dict] = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class InvestigationResponse(BaseModel):
    """Full investigation response with nested data."""

    id: uuid.UUID
    title: str
    status: str
    type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    communications: List[CommunicationResponse] = []
    trust_passport: Optional[TrustPassportResponse] = None

    model_config = {"from_attributes": True}


class InvestigationSummary(BaseModel):
    """Lightweight investigation summary for list views."""

    id: uuid.UUID
    title: str
    status: str
    type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    trust_score: Optional[float] = None
    risk_level: Optional[str] = None

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """Response after uploading a file."""

    communication_id: uuid.UUID
    filename: str
    media_type: str
    status: str
    message: str
