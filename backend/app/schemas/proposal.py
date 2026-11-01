from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.proposal import ProposalStatus


class ProposalCreate(BaseModel):
    title: str
    target_goal: Optional[str] = None
    finding_ids: Optional[List[str]] = []
    markdown_content: Optional[str] = None


class ProposalUpdate(BaseModel):
    title: Optional[str] = None
    target_goal: Optional[str] = None
    markdown_content: Optional[str] = None
    status: Optional[ProposalStatus] = None


class ProposalResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    target_goal: Optional[str] = None
    markdown_content: str
    status: ProposalStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
