# backend/app/models/snapshot.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_run_id = Column(String(36), ForeignKey("scan_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status: 'success', 'error'
    status = Column(String(50), default="success", nullable=False, index=True)
    status_code = Column(Integer, nullable=True)

    # Content
    raw_content = Column(Text, nullable=True)
    normalized_content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256 (64 hex characters)

    # Metadata & Diagnostics
    error_message = Column(Text, nullable=True)
    headers = Column(JSON, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    scan_run = relationship("ScanRun", back_populates="snapshots")
    source = relationship("Source", back_populates="snapshots")
    changes = relationship(
        "Change",
        foreign_keys="[Change.current_snapshot_id]",
        back_populates="current_snapshot",
        cascade="all, delete-orphan",
    )
    changes_as_previous = relationship(
        "Change",
        foreign_keys="[Change.previous_snapshot_id]",
        back_populates="previous_snapshot",
        cascade="all, delete-orphan",
    )
