"""Store extracted facts separately from AI observations.

Revision ID: 20261001_add_resume_analyses
Revises: 20261001_add_resumes
Create Date: 2026-10-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261001_add_resume_analyses"
down_revision = "20261001_add_resumes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("extracted_facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_observations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            ["resume_id"],
            ["resumes.id"],
            name="fk_resume_analyses_resume_id_resumes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id", name="uq_resume_analyses_resume_id"),
    )


def downgrade() -> None:
    op.drop_table("resume_analyses")