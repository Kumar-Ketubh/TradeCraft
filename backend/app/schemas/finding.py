from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.finding import FindingCategory, ConfidenceLevel, VerificationStatus


class EvidenceQuoteResponse(BaseModel):
    id: str
    finding_id: str
    snapshot_id: str
    verbatim_quote: str
    char_offset_start: Optional[int] = None
    char_offset_end: Optional[int] = None
    source_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingResponse(BaseModel):
    id: str
    workspace_id: str
    change_id: Optional[str] = None
    candidate_diff_id: Optional[str] = None
    title: str
    category: FindingCategory
    factual_summary: str
    impact_analysis: str
    recommended_action: str
    confidence_level: ConfidenceLevel
    verification_status: VerificationStatus
    critic_notes: Optional[str] = None
    grounding_score: float
    triage_status: Optional[str] = None
    triage_reason: Optional[str] = None
    created_at: datetime
    evidence_quotes: List[EvidenceQuoteResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FindingFilterParams(BaseModel):
    category: Optional[FindingCategory] = None
    confidence_level: Optional[ConfidenceLevel] = None
    verification_status: Optional[VerificationStatus] = None
    limit: int = 50
    offset: int = 0
