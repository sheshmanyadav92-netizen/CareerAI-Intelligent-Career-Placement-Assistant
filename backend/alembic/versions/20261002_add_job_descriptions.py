"""Add saved job descriptions and versioned analyses.

Revision ID: 20261002_add_job_descriptions
Revises: 20261001_add_resume_analyses
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261002_add_job_descriptions"
down_revision = "20261001_add_resume_analyses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_job_descriptions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_descriptions_user_id_created_at",
        "job_descriptions",
        ["user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "job_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_description_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column(
            "extracted_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_info", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')",
            name="ck_job_analyses_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_description_id"],
            ["job_descriptions.id"],
            name="fk_job_analyses_job_description_id_job_descriptions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_analyses_job_description_id_created_at",
        "job_analyses",
        ["job_description_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_analyses_job_description_id_created_at",
        table_name="job_analyses",
    )
    op.drop_table("job_analyses")
    op.drop_index(
        "ix_job_descriptions_user_id_created_at",
        table_name="job_descriptions",
    )
    op.drop_table("job_descriptions")
