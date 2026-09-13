# backend/app/schemas/workspace.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)

class WorkspaceResponse(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    competitor_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
