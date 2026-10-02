from datetime import datetime

from app.db.base import Base
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_resumes_user_id"),
        UniqueConstraint("storage_key", name="uq_resumes_storage_key"),
        CheckConstraint("size_bytes > 0", name="ck_resumes_size_positive"),
        CheckConstraint("page_count >= 1", name="ck_resumes_page_count_positive"),
        CheckConstraint(
            "extraction_status IN ('ok', 'no_text_found')",
            name="ck_resumes_extraction_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(32), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
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