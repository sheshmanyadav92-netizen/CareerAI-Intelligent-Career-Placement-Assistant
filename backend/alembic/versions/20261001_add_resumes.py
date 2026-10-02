"""Add one resume per user.

Revision ID: 20261001_add_resumes
Revises: 20261001_initial_schema
Create Date: 2026-10-01
"""

import sqlalchemy as sa
from alembic import op

revision = "20261001_add_resumes"
down_revision = "20261001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("extraction_status", sa.String(length=32), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_resumes_size_positive"),
        sa.CheckConstraint("page_count >= 1", name="ck_resumes_page_count_positive"),
        sa.CheckConstraint(
            "extraction_status IN ('ok', 'no_text_found')",
            name="ck_resumes_extraction_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_resumes_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_resumes_storage_key"),
        sa.UniqueConstraint("user_id", name="uq_resumes_user_id"),
    )


def downgrade() -> None:
    op.drop_table("resumes")