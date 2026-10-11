# backend/app/adapters/base.py
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict
import httpx

from app.adapters.hashing import compute_content_hash

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT_SECONDS = 6.0
MAX_CONTENT_BYTES = 2_000_000  # 2MB max payload cap to prevent massive streams from hanging


@dataclass
class AdapterResult:
    """
    Normalized result container for adapter fetch and parse operations.
    """
    url: str
    status: str                          # "success" or "error"
    http_status: Optional[int] = None    # e.g., 200, 403, 404, 500
    raw_content: Optional[str] = None
    normalized_content: Optional[str] = None
    content_hash: Optional[str] = None   # 64-character SHA-256 lowercase hex string
    error_message: Optional[str] = None


class BaseAdapter(ABC):
    """
    Abstract base class for source ingestion adapters.
    """

    def __init__(
        self,
        url: str,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.url = url
        self.client = client
        self.timeout = timeout
        self.user_agent = user_agent

    def get_headers(self) -> Dict[str, str]:
        """HTTP headers to include in fetch requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
        }

    @abstractmethod
    def normalize(self, raw_content: str) -> str:
        """
        Normalize raw source content into clean, deterministic text.
        Must strip noise, dynamic elements, and normalize whitespace.
        """
        pass

    async def fetch(self) -> AdapterResult:
        """
        Non-blocking, fault-tolerant fetch execution.
        Never raises uncaught network exceptions (e.g. 403, 404, 500, timeouts).
        """
        headers = self.get_headers()
        connect_timeout = min(4.0, self.timeout)
        timeout = httpx.Timeout(self.timeout, connect=connect_timeout)

        async def _do_fetch(client: httpx.AsyncClient) -> AdapterResult:
            response = await client.get(
                self.url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )
            if response.status_code >= 400:
                reason = response.reason_phrase or "Error"
                return AdapterResult(
                    url=self.url,
                    status="error",
                    http_status=response.status_code,
                    raw_content=None,
                    normalized_content=None,
                    content_hash=None,
                    error_message=f"HTTP {response.status_code}: {reason}",
                )

            raw_content = response.text
            normalized = self.normalize(raw_content)
            content_hash = compute_content_hash(normalized)
            return AdapterResult(
                url=self.url,
                status="success",
                http_status=response.status_code,
                raw_content=raw_content,
                normalized_content=normalized,
                content_hash=content_hash,
                error_message=None,
            )

        try:
            if self.client is not None:
                return await asyncio.wait_for(_do_fetch(self.client), timeout=self.timeout + 0.5)
            async with httpx.AsyncClient() as client:
                return await asyncio.wait_for(_do_fetch(client), timeout=self.timeout + 0.5)
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            return AdapterResult(
                url=self.url,
                status="error",
                http_status=None,
                error_message=f"Request timeout: {exc or 'Timed out'}",
            )
        except httpx.RequestError as exc:
            return AdapterResult(
                url=self.url,
                status="error",
                http_status=None,
                error_message=f"Network error: {exc}",
            )
        except Exception as exc:
            return AdapterResult(
                url=self.url,
                status="error",
                http_status=None,
                error_message=f"Unexpected error: {exc}",
            )
