# backend/app/models/change.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base


class Change(Base):
    __tablename__ = "changes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    competitor_id = Column(String(36), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_run_id = Column(String(36), ForeignKey("scan_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_snapshot_id = Column(String(36), ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=True, index=True)
    current_snapshot_id = Column(String(36), ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False, index=True)

    # Core change payload
    change_hash = Column(String(64), nullable=False, index=True)
    change_type = Column(String(50), default="modification", nullable=False, index=True)
    category = Column(String(50), default="unknown", nullable=False, index=True)
    is_meaningful = Column(Boolean, default=True, nullable=False, index=True)
    significance_score = Column(Float, default=0.0, nullable=False)
    summary = Column(Text, nullable=True)
    diff_unified = Column(Text, nullable=False)
    diff_stats = Column(JSON, nullable=True)

    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="changes")
    competitor = relationship("Competitor", back_populates="changes")
    source = relationship("Source", back_populates="changes")
    scan_run = relationship("ScanRun", back_populates="changes")
    previous_snapshot = relationship(
        "Snapshot",
        foreign_keys=[previous_snapshot_id],
        back_populates="changes_as_previous",
    )
    current_snapshot = relationship(
        "Snapshot",
        foreign_keys=[current_snapshot_id],
        back_populates="changes",
    )
