"""Initial schema — all core tables.

Revision ID: 001_initial
Revises: None
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── investigations ──────────────────────────────────────
    op.create_table(
        "investigations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("type", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── communications ──────────────────────────────────────
    op.create_table(
        "communications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("media_type", sa.String(50), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=True),
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column(
            "processing_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("processing_step", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_communications_investigation_id",
        "communications",
        ["investigation_id"],
    )

    # ── claims ──────────────────────────────────────────────
    op.create_table(
        "claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "communication_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("predicate", sa.String(500), nullable=False),
        sa.Column("object", sa.String(500), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_claims_communication_id", "claims", ["communication_id"]
    )

    # ── evidence ────────────────────────────────────────────
    op.create_table(
        "evidence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "claim_id",
            UUID(as_uuid=True),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("supports", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("explanation", sa.Text, nullable=False, server_default=""),
        sa.Column("raw_data", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_evidence_claim_id", "evidence", ["claim_id"])

    # ── trust_passports ─────────────────────────────────────
    op.create_table(
        "trust_passports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("overall_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "risk_level", sa.String(50), nullable=False, server_default="unknown"
        ),
        sa.Column("recommendation", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "media_authenticity_score",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "claim_verification_score",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "source_credibility_score",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "evidence_strength_score",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("details_json", JSON, nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("trust_passports")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("communications")
    op.drop_table("investigations")
