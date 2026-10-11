# backend/app/models/scan_run.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    competitor_id = Column(String(36), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=True, index=True)

    # Status: 'pending', 'running', 'completed', 'partial', 'failed'
    status = Column(String(50), default="pending", nullable=False, index=True)
    total_sources = Column(Integer, default=0, nullable=False)
    successful_sources = Column(Integer, default=0, nullable=False)
    failed_sources = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="scan_runs")
    competitor = relationship("Competitor", back_populates="scan_runs")
    snapshots = relationship("Snapshot", back_populates="scan_run", cascade="all, delete-orphan")
    changes = relationship("Change", back_populates="scan_run", cascade="all, delete-orphan")
