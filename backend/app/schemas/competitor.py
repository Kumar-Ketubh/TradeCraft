# backend/app/schemas/competitor.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    website: Optional[str] = None
    monitoring_enabled: bool = True

class CompetitorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    website: Optional[str] = None
    monitoring_enabled: Optional[bool] = None

class CompetitorResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    monitoring_enabled: bool
    created_at: datetime
    updated_at: datetime
    source_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
