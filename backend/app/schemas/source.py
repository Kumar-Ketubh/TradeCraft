# backend/app/schemas/source.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

VALID_SOURCE_TYPES = [
    "website",
    "product_page",
    "pricing",
    "blog",
    "documentation",
    "rss",
    "news",
    "other",
]

class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    url: str = Field(..., min_length=1, max_length=500)
    source_type: str = Field("website", description="One of: website, product_page, pricing, blog, documentation, rss, news, other")
    monitoring_enabled: bool = True

class SourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    source_type: Optional[str] = None
    monitoring_enabled: Optional[bool] = None

class SourceResponse(BaseModel):
    id: str
    competitor_id: str
    name: str
    url: str
    source_type: str
    monitoring_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
