# backend/app/adapters/__init__.py
from app.adapters.base import (
    AdapterResult,
    BaseAdapter,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
)
from app.adapters.factory import get_adapter_for_source
from app.adapters.hashing import compute_content_hash
from app.adapters.html_adapter import HtmlAdapter
from app.adapters.rss_adapter import RssAdapter

__all__ = [
    "AdapterResult",
    "BaseAdapter",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_USER_AGENT",
    "HtmlAdapter",
    "RssAdapter",
    "compute_content_hash",
    "get_adapter_for_source",
]
