"""Step 5 initial schema baseline.

Revision ID: 20260318_0001
Revises:
Create Date: 2026-03-18 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260318_0001"
down_revision = None
branch_labels = None
depends_on = None

user_role_enum = postgresql.ENUM("operator", "sales", "manager", name="user_role", create_type=False)
user_status_enum = postgresql.ENUM("active", "disabled", name="user_status", create_type=False)
lead_status_enum = postgresql.ENUM(
    "new", "contacted", "converted", "invalid", name="lead_status", create_type=False
)
opportunity_stage_enum = postgresql.ENUM(
    "initial",
    "proposal",
    "negotiation",
    "won",
    "lost",
    name="opportunity_stage",
    create_type=False,
)
content_task_type_enum = postgresql.ENUM(
    "copywriting", "image", "video_script", name="content_task_type", create_type=False
)
content_task_status_enum = postgresql.ENUM(
    "pending",
    "running",
    "succeeded",
    "failed",
    name="content_task_status",
    create_type=False,
)
kb_message_role_enum = postgresql.ENUM("user", "assistant", name="kb_message_role", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    user_status_enum.create(bind, checkfirst=True)
    lead_status_enum.create(bind, checkfirst=True)
    opportunity_stage_enum.create(bind, checkfirst=True)
    content_task_type_enum.create(bind, checkfirst=True)
    content_task_status_enum.create(bind, checkfirst=True)
    kb_message_role_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("status", user_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("company_name", sa.String(length=128), nullable=False),
        sa.Column("source_channel", sa.String(length=64), nullable=False),
        sa.Column("status", lead_status_enum, nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("latest_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone", name="uq_leads_phone"),
    )
    op.create_index("ix_leads_company_name_name", "leads", ["company_name", "name"], unique=False)
    op.create_index(
        "ix_leads_owner_user_id_status_created_at",
        "leads",
        ["owner_user_id", "status", "created_at"],
        unique=False,
    )

    op.create_table(
        "lead_merge_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merged_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("merge_reason", sa.String(length=64), nullable=False),
        sa.Column("operator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(length=128), nullable=False),
        sa.Column("contact_name", sa.String(length=64), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id", name="uq_customers_lead_id"),
    )

    op.create_table(
        "follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("next_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_follow_ups_lead_id_created_at", "follow_ups", ["lead_id", "created_at"], unique=False)

    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage", opportunity_stage_enum, nullable=False),
        sa.Column("amount_estimate", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunities_owner_user_id_stage_updated_at",
        "opportunities",
        ["owner_user_id", "stage", "updated_at"],
        unique=False,
    )

    op.create_table(
        "deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deal_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("deal_date", sa.Date(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", name="uq_deals_opportunity_id"),
    )
    op.create_index("ix_deals_deal_date", "deals", ["deal_date"], unique=False)

    op.create_table(
        "content_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", content_task_type_enum, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", content_task_status_enum, nullable=False),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_content_tasks_created_by_status_created_at",
        "content_tasks",
        ["created_by", "status", "created_at"],
        unique=False,
    )

    op.create_table(
        "kb_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_key", name="uq_kb_sessions_session_key"),
    )

    op.create_table(
        "kb_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", kb_message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(role != 'assistant') OR (source_refs IS NOT NULL)",
            name="assistant_source_refs",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["kb_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kb_messages_session_id_created_at",
        "kb_messages",
        ["session_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("before_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_actor_user_id_created_at",
        "audit_logs",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_audit_logs_action_created_at", "audit_logs", ["action", "created_at"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("kb_messages")
    op.drop_table("kb_sessions")
    op.drop_table("content_tasks")
    op.drop_table("deals")
    op.drop_table("opportunities")
    op.drop_table("follow_ups")
    op.drop_table("customers")
    op.drop_table("lead_merge_logs")
    op.drop_table("leads")
    op.drop_table("users")

    bind = op.get_bind()
    kb_message_role_enum.drop(bind, checkfirst=True)
    content_task_status_enum.drop(bind, checkfirst=True)
    content_task_type_enum.drop(bind, checkfirst=True)
    opportunity_stage_enum.drop(bind, checkfirst=True)
    lead_status_enum.drop(bind, checkfirst=True)
    user_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
