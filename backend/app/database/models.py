"""
MarketTrust AI — SQLAlchemy ORM Models.

Defines the core data models: Investigation, Communication, Claim, Evidence,
and TrustPassport with their relationships. Compatible with both PostgreSQL and SQLite.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


class Investigation(Base):
    """An investigation into a financial communication."""

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending | uploading | processing | completed | failed
    type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # video | image | email | website
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    communications: Mapped[List["Communication"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", lazy="selectin"
    )
    trust_passport: Mapped[Optional["TrustPassport"]] = relationship(
        back_populates="investigation",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Communication(Base):
    """A piece of media uploaded for investigation (video, image, email, URL)."""

    __tablename__ = "communications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )  # MinIO object key
    media_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # video | image | email | website
    original_filename: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True
    )  # For website investigations
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Full extracted text
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Raw metadata from extraction
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending | extracting | analyzing | completed | failed
    processing_step: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Current pipeline step description
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        back_populates="communications", lazy="selectin"
    )
    claims: Mapped[List["Claim"]] = relationship(
        back_populates="communication", cascade="all, delete-orphan", lazy="selectin"
    )


class Claim(Base):
    """A factual claim extracted from a communication by the LLM."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    communication_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("communications.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    predicate: Mapped[str] = mapped_column(String(500), nullable=False)
    object: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    raw_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Original text this claim was extracted from
    category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # financial | regulatory | performance | identity
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    communication: Mapped["Communication"] = relationship(
        back_populates="claims", lazy="selectin"
    )
    evidence: Mapped[List["Evidence"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", lazy="selectin"
    )


class Evidence(Base):
    """Evidence gathered to verify or refute a claim."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # chromadb | sebi_db | llm_reasoning | url_check | whois
    source_url: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True
    )
    supports: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_data: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Raw verification data
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    claim: Mapped["Claim"] = relationship(back_populates="evidence", lazy="selectin")


class TrustPassport(Base):
    """The final trust assessment for an investigation."""

    __tablename__ = "trust_passports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    overall_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # 0-100
    risk_level: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown"
    )  # low | medium | high | critical
    recommendation: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )
    media_authenticity_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    claim_verification_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    source_credibility_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    evidence_strength_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    details_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Full breakdown
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        back_populates="trust_passport", lazy="selectin"
    )
