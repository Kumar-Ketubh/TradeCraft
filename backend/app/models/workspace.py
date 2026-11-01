# backend/app/models/workspace.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    product_name = Column(String(255), nullable=True)
    value_proposition = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    pricing_summary = Column(Text, nullable=True)
    strategic_focus = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner = relationship("User", back_populates="workspaces")
    competitors = relationship("Competitor", back_populates="workspace", cascade="all, delete-orphan")
    scan_runs = relationship("ScanRun", back_populates="workspace", cascade="all, delete-orphan")
    changes = relationship("Change", back_populates="workspace", cascade="all, delete-orphan")
    findings = relationship("IntelligenceFinding", back_populates="workspace", cascade="all, delete-orphan")
    proposals = relationship("Proposal", back_populates="workspace", cascade="all, delete-orphan")
