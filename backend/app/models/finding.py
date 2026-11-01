import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class FindingCategory(str, enum.Enum):
    PRICING_CHANGE = "PRICING_CHANGE"
    FEATURE_RELEASE = "FEATURE_RELEASE"
    POSITIONING = "POSITIONING"
    DEPRECATION = "DEPRECATION"
    OTHER = "OTHER"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VerificationStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    DOWNGRADED = "DOWNGRADED"
    REJECTED = "REJECTED"


class IntelligenceFinding(Base):
    __tablename__ = "intelligence_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    change_id = Column(String(36), ForeignKey("changes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(512), nullable=False)
    category = Column(String(64), default=FindingCategory.FEATURE_RELEASE.value, nullable=False)
    factual_summary = Column(Text, nullable=False)
    impact_analysis = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    confidence_level = Column(String(32), default=ConfidenceLevel.MEDIUM.value, nullable=False)
    verification_status = Column(String(32), default=VerificationStatus.VERIFIED.value, nullable=False)
    critic_notes = Column(Text, nullable=True)
    grounding_score = Column(Float, default=100.0, nullable=False)  # Evidence Grounding Accuracy (EGA) %
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    workspace = relationship("Workspace", back_populates="findings")
    change = relationship("Change", back_populates="findings")
    evidence_quotes = relationship("EvidenceQuote", back_populates="finding", cascade="all, delete-orphan")

    @property
    def candidate_diff_id(self):
        return self.change_id

    @property
    def triage_status(self):
        if self.change:
            return "HIGH_IMPACT" if self.change.is_meaningful else "TRIVIAL"
        return None

    @property
    def triage_reason(self):
        return self.change.summary if self.change else None


class EvidenceQuote(Base):
    __tablename__ = "evidence_quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id = Column(String(36), ForeignKey("intelligence_findings.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(String(36), ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    verbatim_quote = Column(Text, nullable=False)
    char_offset_start = Column(Integer, nullable=True)
    char_offset_end = Column(Integer, nullable=True)
    source_url = Column(String(2048), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    finding = relationship("IntelligenceFinding", back_populates="evidence_quotes")
    snapshot = relationship("Snapshot", back_populates="quotes")
