# backend/app/schemas/change.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, model_validator


class ChangeResponse(BaseModel):
    id: str
    workspace_id: str
    competitor_id: str
    source_id: str
    scan_run_id: str
    previous_snapshot_id: Optional[str] = None
    current_snapshot_id: str
    change_hash: str
    change_type: str = "modification"
    category: str = "unknown"
    is_meaningful: bool = True
    significance_score: float = 0.0
    summary: Optional[str] = None
    diff_stats: Optional[Dict[str, Any]] = None
    detected_at: datetime
    competitor_name: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_related_context(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            comp = getattr(data, "competitor", None)
            src = getattr(data, "source", None)
            d = {
                "id": getattr(data, "id", None),
                "workspace_id": getattr(data, "workspace_id", None),
                "competitor_id": getattr(data, "competitor_id", None),
                "source_id": getattr(data, "source_id", None),
                "scan_run_id": getattr(data, "scan_run_id", None),
                "previous_snapshot_id": getattr(data, "previous_snapshot_id", None),
                "current_snapshot_id": getattr(data, "current_snapshot_id", None),
                "change_hash": getattr(data, "change_hash", None),
                "change_type": getattr(data, "change_type", "modification"),
                "category": getattr(data, "category", "unknown"),
                "is_meaningful": getattr(data, "is_meaningful", True),
                "significance_score": getattr(data, "significance_score", 0.0),
                "summary": getattr(data, "summary", None),
                "diff_stats": getattr(data, "diff_stats", None),
                "detected_at": getattr(data, "detected_at", None),
                "competitor_name": getattr(comp, "name", None) if comp else getattr(data, "competitor_name", None),
                "source_name": getattr(src, "name", None) if src else getattr(data, "source_name", None),
                "source_url": getattr(src, "url", None) if src else getattr(data, "source_url", None),
            }
            if hasattr(data, "diff_unified"):
                d["diff_unified"] = getattr(data, "diff_unified")
            return d
        return data


class ChangeDetailResponse(ChangeResponse):
    diff_unified: str

    model_config = ConfigDict(from_attributes=True)
