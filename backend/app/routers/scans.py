# backend/app/routers/scans.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.schemas.scan import (
    ScanRunResponse,
    ScanRunDetailResponse,
    SnapshotResponse,
)
from app.services.scan_service import ScanService

router = APIRouter(tags=["Scans"])


def get_scan_service(db: Session = Depends(get_db)) -> ScanService:
    """Dependency provider for ScanService to allow test override."""
    return ScanService(db=db)


@router.post(
    "/workspaces/{workspace_id}/scan",
    response_model=ScanRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a workspace-wide scan across all active sources",
)
async def trigger_workspace_scan(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    scan_service: ScanService = Depends(get_scan_service),
):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )

    return await scan_service.scan_workspace(workspace_id)


@router.post(
    "/competitors/{competitor_id}/scan",
    response_model=ScanRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a scan for a single competitor's active sources",
)
async def trigger_competitor_scan(
    competitor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    scan_service: ScanService = Depends(get_scan_service),
):
    competitor = (
        db.query(Competitor)
        .join(Workspace, Competitor.workspace_id == Workspace.id)
        .filter(Competitor.id == competitor_id, Workspace.user_id == current_user.id)
        .first()
    )
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found or access denied",
        )

    return await scan_service.scan_competitor(competitor_id)


@router.get(
    "/workspaces/{workspace_id}/scans",
    response_model=List[ScanRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List scan runs for a workspace",
)
def list_workspace_scans(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )

    scans = (
        db.query(ScanRun)
        .filter(ScanRun.workspace_id == workspace_id)
        .order_by(ScanRun.created_at.desc())
        .all()
    )
    return [ScanRunResponse.model_validate(s) for s in scans]


@router.get(
    "/scans/{scan_id}",
    response_model=ScanRunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed view of a scan run including snapshots",
)
def get_scan_detail(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan_run = (
        db.query(ScanRun)
        .join(Workspace, ScanRun.workspace_id == Workspace.id)
        .filter(ScanRun.id == scan_id, Workspace.user_id == current_user.id)
        .first()
    )
    if not scan_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan run not found or access denied",
        )

    snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.scan_run_id == scan_id)
        .order_by(Snapshot.created_at.asc())
        .all()
    )

    detail = ScanRunDetailResponse.model_validate(scan_run)
    detail.snapshots = [SnapshotResponse.model_validate(s) for s in snapshots]
    return detail


@router.get(
    "/sources/{source_id}/snapshots",
    response_model=List[SnapshotResponse],
    status_code=status.HTTP_200_OK,
    summary="List historical snapshots for a given source",
)
def list_source_snapshots(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source = (
        db.query(Source)
        .join(Competitor, Source.competitor_id == Competitor.id)
        .join(Workspace, Competitor.workspace_id == Workspace.id)
        .filter(Source.id == source_id, Workspace.user_id == current_user.id)
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found or access denied",
        )

    snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.source_id == source_id)
        .order_by(Snapshot.created_at.desc())
        .all()
    )
    return [SnapshotResponse.model_validate(s) for s in snapshots]
