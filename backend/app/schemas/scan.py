# backend/app/schemas/scan.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, computed_field


class SnapshotBase(BaseModel):
    scan_run_id: str
    source_id: str
    status: str
    status_code: Optional[int] = None
    content_hash: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None


class SnapshotResponse(BaseModel):
    id: str
    scan_run_id: str
    source_id: str
    status: str
    status_code: Optional[int] = None
    content_hash: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    created_at: datetime
    normalized_content: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SnapshotDetailResponse(SnapshotResponse):
    raw_content: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ScanRunBase(BaseModel):
    workspace_id: str
    competitor_id: Optional[str] = None


class ScanRunCreate(ScanRunBase):
    pass


class ScanRunResponse(BaseModel):
    id: str
    workspace_id: str
    competitor_id: Optional[str] = None
    status: str
    total_sources: int
    successful_sources: int
    failed_sources: int
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def scan_run_id(self) -> str:
        return self.id


class ScanRunDetailResponse(ScanRunResponse):
    snapshots: List[SnapshotResponse] = []

    model_config = ConfigDict(from_attributes=True)
