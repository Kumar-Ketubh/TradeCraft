# backend/app/services/scan_service.py
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Tuple
import httpx
from sqlalchemy.orm import Session

from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.models.competitor import Competitor
from app.models.source import Source
from app.adapters.factory import get_adapter_for_source
from app.adapters.base import AdapterResult, DEFAULT_TIMEOUT_SECONDS
from app.services.change_service import ChangeDetectionService

logger = logging.getLogger(__name__)


class ScanService:
    """
    Service responsible for orchestrating concurrent source scans,
    persisting snapshots, and tracking scan run progression.
    """

    def __init__(
        self,
        db: Session,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.db = db
        self.client = client
        self.timeout = timeout

    async def scan_workspace(self, workspace_id: str) -> ScanRun:
        """
        Scan all active sources across all active competitors within a workspace.
        """
        sources = (
            self.db.query(Source)
            .join(Competitor, Source.competitor_id == Competitor.id)
            .filter(
                Competitor.workspace_id == workspace_id,
                Competitor.monitoring_enabled.is_(True),
                Source.monitoring_enabled.is_(True),
            )
            .all()
        )

        now = datetime.now(timezone.utc)
        if not sources:
            scan_run = ScanRun(
                workspace_id=workspace_id,
                competitor_id=None,
                status="completed",
                total_sources=0,
                successful_sources=0,
                failed_sources=0,
                error_message=None,
                created_at=now,
                completed_at=now,
            )
            self.db.add(scan_run)
            self.db.commit()
            self.db.refresh(scan_run)
            return scan_run

        scan_run = ScanRun(
            workspace_id=workspace_id,
            competitor_id=None,
            status="running",
            total_sources=len(sources),
            successful_sources=0,
            failed_sources=0,
            created_at=now,
            completed_at=None,
        )
        self.db.add(scan_run)
        self.db.commit()
        self.db.refresh(scan_run)

        return await self._execute_scan(scan_run, sources)

    async def scan_competitor(self, competitor_id: str) -> ScanRun:
        """
        Scan all active sources for a single competitor.
        """
        competitor = self.db.query(Competitor).filter(Competitor.id == competitor_id).first()
        if not competitor:
            raise ValueError(f"Competitor '{competitor_id}' not found")

        sources = (
            self.db.query(Source)
            .filter(
                Source.competitor_id == competitor_id,
                Source.monitoring_enabled.is_(True),
            )
            .all()
        )

        now = datetime.now(timezone.utc)
        if not sources:
            scan_run = ScanRun(
                workspace_id=competitor.workspace_id,
                competitor_id=competitor.id,
                status="completed",
                total_sources=0,
                successful_sources=0,
                failed_sources=0,
                error_message=None,
                created_at=now,
                completed_at=now,
            )
            self.db.add(scan_run)
            self.db.commit()
            self.db.refresh(scan_run)
            return scan_run

        scan_run = ScanRun(
            workspace_id=competitor.workspace_id,
            competitor_id=competitor.id,
            status="running",
            total_sources=len(sources),
            successful_sources=0,
            failed_sources=0,
            created_at=now,
            completed_at=None,
        )
        self.db.add(scan_run)
        self.db.commit()
        self.db.refresh(scan_run)

        return await self._execute_scan(scan_run, sources)

    async def _execute_scan(self, scan_run: ScanRun, sources: List[Source]) -> ScanRun:
        """
        Execute concurrent source fetching and snapshot persistence.
        """
        if self.client is not None:
            return await self._run_fetch_batch(scan_run, sources, self.client)
        async with httpx.AsyncClient() as client:
            return await self._run_fetch_batch(scan_run, sources, client)

    async def _run_fetch_batch(
        self,
        scan_run: ScanRun,
        sources: List[Source],
        client: httpx.AsyncClient,
    ) -> ScanRun:
        async def _fetch_single(source: Source) -> Tuple[Source, AdapterResult, int]:
            start = time.perf_counter()
            try:
                adapter = get_adapter_for_source(source, client=client, timeout=self.timeout)
                result = await asyncio.wait_for(adapter.fetch(), timeout=self.timeout + 1.0)
            except asyncio.TimeoutError:
                result = AdapterResult(
                    url=str(getattr(source, "url", "")),
                    status="error",
                    http_status=None,
                    error_message=f"Request timeout: Source fetch timed out after {self.timeout}s",
                )
            except Exception as exc:
                result = AdapterResult(
                    url=str(getattr(source, "url", "")),
                    status="error",
                    http_status=None,
                    error_message=f"Adapter execution failed: {exc}",
                )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return source, result, elapsed_ms

        tasks = [_fetch_single(src) for src in sources]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_sources = 0
        failed_sources = 0
        successful_snapshots: List[Snapshot] = []

        for idx, item in enumerate(raw_results):
            source = sources[idx]
            now = datetime.now(timezone.utc)
            if isinstance(item, Exception):
                snapshot = Snapshot(
                    scan_run_id=scan_run.id,
                    source_id=source.id,
                    status="error",
                    status_code=None,
                    raw_content=None,
                    normalized_content=None,
                    content_hash=None,
                    error_message=str(item),
                    response_time_ms=0,
                    created_at=now,
                )
                failed_sources += 1
            else:
                src, result, elapsed_ms = item
                if result.status == "success":
                    snapshot = Snapshot(
                        scan_run_id=scan_run.id,
                        source_id=src.id,
                        status="success",
                        status_code=result.http_status,
                        raw_content=result.raw_content,
                        normalized_content=result.normalized_content,
                        content_hash=result.content_hash,
                        error_message=None,
                        response_time_ms=elapsed_ms,
                        created_at=now,
                    )
                    successful_sources += 1
                    successful_snapshots.append(snapshot)
                else:
                    snapshot = Snapshot(
                        scan_run_id=scan_run.id,
                        source_id=src.id,
                        status="error",
                        status_code=result.http_status,
                        raw_content=result.raw_content,
                        normalized_content=result.normalized_content,
                        content_hash=result.content_hash,
                        error_message=result.error_message or "Fetch failed",
                        response_time_ms=elapsed_ms,
                        created_at=now,
                    )
                    failed_sources += 1
            self.db.add(snapshot)

        # Flush so newly added snapshots have assigned primary keys (snapshot.id)
        self.db.flush()

        # Run change detection across all newly created successful snapshots
        try:
            change_service = ChangeDetectionService(db=self.db)
            for snap in successful_snapshots:
                change_service.detect_change_for_snapshot(snap)
        except Exception as exc:
            logger.warning(f"Change detection error during scan batch: {exc}")

        scan_run.successful_sources = successful_sources
        scan_run.failed_sources = failed_sources
        scan_run.completed_at = datetime.now(timezone.utc)

        if failed_sources == 0:
            scan_run.status = "completed"
            scan_run.error_message = None
        elif successful_sources == 0:
            scan_run.status = "failed"
            scan_run.error_message = f"All {len(sources)} sources failed to fetch."
        else:
            scan_run.status = "partial"
            scan_run.error_message = f"{failed_sources} of {len(sources)} sources failed to fetch."

        self.db.commit()
        self.db.refresh(scan_run)
        return scan_run


async def scan_workspace(
    workspace_id: str,
    db: Session,
    client: Optional[httpx.AsyncClient] = None,
) -> ScanRun:
    """Convenience helper to scan a workspace."""
    service = ScanService(db=db, client=client)
    return await service.scan_workspace(workspace_id)


async def scan_competitor(
    competitor_id: str,
    db: Session,
    client: Optional[httpx.AsyncClient] = None,
) -> ScanRun:
    """Convenience helper to scan a competitor."""
    service = ScanService(db=db, client=client)
    return await service.scan_competitor(competitor_id)
