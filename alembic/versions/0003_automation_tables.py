"""Add automation jobs and audit tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_automation_tables"
down_revision = "0002_admin_foundations"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("automation_rules", sa.Column("tenant_id", UUID, nullable=True))
    op.add_column("automation_rules", sa.Column("trigger_type", sa.String(length=32), nullable=False, server_default="event"))
    op.add_column("automation_rules", sa.Column("schedule_expression", sa.String(length=120), nullable=True))
    op.add_column("automation_rules", sa.Column("action_type", sa.String(length=32), nullable=False, server_default="webhook"))
    op.add_column("automation_rules", sa.Column("throttle_seconds", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("automation_rules", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("automation_rules", sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("automation_rules", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE automation_rules
           SET tenant_id = brands.tenant_id
          FROM brands
         WHERE brands.id = automation_rules.brand_id
        """
    )
    op.alter_column("automation_rules", "tenant_id", existing_type=UUID, nullable=False)

    op.create_foreign_key(
        "fk_automation_rules_tenant",
        "automation_rules",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "automation_jobs",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("rule_id", UUID, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("brand_id", UUID, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["rule_id"], ["automation_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "automation_audit",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("rule_id", UUID, nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["automation_rules.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("automation_audit")
    op.drop_table("automation_jobs")
    op.drop_constraint("fk_automation_rules_tenant", "automation_rules", type_="foreignkey")
    op.drop_column("automation_rules", "paused_at")
    op.drop_column("automation_rules", "last_run_at")
    op.drop_column("automation_rules", "max_retries")
    op.drop_column("automation_rules", "throttle_seconds")
    op.drop_column("automation_rules", "action_type")
    op.drop_column("automation_rules", "schedule_expression")
    op.drop_column("automation_rules", "trigger_type")
    op.drop_column("automation_rules", "tenant_id")
