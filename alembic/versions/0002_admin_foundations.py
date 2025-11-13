"""Create admin support tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_admin_foundations"
down_revision = "0001_initial_placeholder"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "embed_configs",
        sa.Column("id", UUID, primary_key=True, nullable=False),
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
            onupdate=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", UUID, nullable=False, unique=True),
        sa.Column("theme", sa.JSON(), nullable=True),
        sa.Column("widget_options", sa.JSON(), nullable=True),
        sa.Column("handshake_salt", sa.String(length=64), nullable=False),
        sa.Column("token_ttl_seconds", sa.Integer(), nullable=False, server_default="900"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "policy_versions",
        sa.Column("id", UUID, primary_key=True, nullable=False),
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
            onupdate=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=True),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "version", name="uq_policy_versions_tenant_version"),
    )

    op.create_table(
        "channel_secrets",
        sa.Column("id", UUID, primary_key=True, nullable=False),
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
            onupdate=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channel_id", UUID, nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="hmac"),
        sa.Column("secret_hash", sa.String(length=128), nullable=False),
        sa.Column("secret_reference", sa.String(length=512), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["channel_configs.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "audit_log_entries",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("tenant_id", UUID, nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False, server_default="user"),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=120), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "knowledge_assets",
        sa.Column("id", UUID, primary_key=True, nullable=False),
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
            onupdate=sa.func.now(),
        ),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("brand_id", UUID, nullable=False),
        sa.Column("knowledge_source_id", UUID, nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("visibility", sa.String(length=16), nullable=False, server_default="private"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", UUID, primary_key=True, nullable=False),
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
            onupdate=sa.func.now(),
        ),
        sa.Column("knowledge_source_id", UUID, nullable=False, unique=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("brand_id", UUID, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_chunks", sa.Integer(), nullable=True),
        sa.Column("processed_chunks", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("logs", sa.JSON(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["knowledge_source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "policy_snapshots",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("policy_version_id", UUID, nullable=False),
        sa.Column("previous_version", sa.Integer(), nullable=True),
        sa.Column("diff_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "retrieval_configs",
        sa.Column("id", UUID, primary_key=True, nullable=False),
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
            onupdate=sa.func.now(),
        ),
        sa.Column("tenant_id", UUID, nullable=False, unique=True),
        sa.Column("hybrid_weight", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("min_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_documents", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("context_budget_tokens", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("fallback_llm", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("retrieval_configs")
    op.drop_table("policy_snapshots")
    op.drop_table("ingestion_jobs")
    op.drop_table("knowledge_assets")
    op.drop_table("audit_log_entries")
    op.drop_table("channel_secrets")
    op.drop_table("policy_versions")
    op.drop_table("embed_configs")
