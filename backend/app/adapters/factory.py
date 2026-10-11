# backend/app/adapters/factory.py
from typing import Any, Optional
import httpx

from app.adapters.base import BaseAdapter, DEFAULT_TIMEOUT_SECONDS
from app.adapters.html_adapter import HtmlAdapter
from app.adapters.rss_adapter import RssAdapter


def get_adapter_for_source(
    source: Any,
    client: Optional[httpx.AsyncClient] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> BaseAdapter:
    """
    Factory function to instantiate the appropriate adapter for a given Source.
    Supports SQLAlchemy models, Pydantic schemas, or dictionaries.
    """
    if isinstance(source, dict):
        source_type = source.get("source_type", "")
        url = source.get("url", "")
    else:
        source_type = getattr(source, "source_type", "")
        url = getattr(source, "url", "")

    url_str = str(url or "").strip()
    url_lower = url_str.lower()

    is_rss = (
        str(source_type).lower() == "rss"
        or url_lower.endswith((".xml", ".rss", ".atom", "/feed", "/rss", "/atom", "/rss.xml", "/feed.xml"))
        or "/feed/" in url_lower
        or "/rss/" in url_lower
        or "format=rss" in url_lower
        or "format=atom" in url_lower
    )

    if is_rss:
        return RssAdapter(url=url_str, client=client, timeout=timeout)
    return HtmlAdapter(url=url_str, client=client, timeout=timeout)
