# backend/app/routers/changes.py
"""
Changes router for TradeCraft competitive intelligence.

Provides endpoints for querying detected changes by workspace or scan run,
inspecting unified diffs and statistics, and filtering by meaningfulness,
category, and competitor with strict multi-tenant isolation.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.change import Change
from app.models.competitor import Competitor
from app.models.scan_run import ScanRun
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.change import ChangeDetailResponse, ChangeResponse

router = APIRouter(tags=["Changes"])


@router.get(
    "/workspaces/{workspace_id}/changes",
    response_model=List[ChangeResponse],
    summary="List detected changes in a workspace with optional filters",
)
def list_workspace_changes(
    workspace_id: str = "",
    id: Optional[str] = None,
    is_meaningful: Optional[bool] = Query(
        None, description="Filter by meaningfulness (true or false)"
    ),
    category: Optional[str] = Query(
        None, description="Filter by change category (e.g. pricing_change, feature_announcement)"
    ),
    competitor_id: Optional[str] = Query(
        None, description="Filter by specific competitor ID"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of changes to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve detected changes for a workspace belonging to the current user.
    Supports filtering by meaningfulness, category, and competitor, ordered newest first.
    """
    target_workspace_id = workspace_id or id
    if not target_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )

    # 1. Multi-tenant isolation: verify workspace exists and belongs to current user
    workspace = (
        db.query(Workspace)
        .filter(
            Workspace.id == target_workspace_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )

    # 2. If competitor_id is supplied, verify it belongs to this workspace
    if competitor_id:
        competitor = (
            db.query(Competitor)
            .filter(
                Competitor.id == competitor_id,
                Competitor.workspace_id == target_workspace_id,
            )
            .first()
        )
        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found or access denied",
            )

    # 3. Build query with eager loading for competitor and source
    query = (
        db.query(Change)
        .options(joinedload(Change.competitor), joinedload(Change.source))
        .filter(Change.workspace_id == target_workspace_id)
    )

    if is_meaningful is not None:
        query = query.filter(Change.is_meaningful == is_meaningful)
    if category:
        query = query.filter(Change.category == category)
    if competitor_id:
        query = query.filter(Change.competitor_id == competitor_id)

    query = query.order_by(Change.detected_at.desc(), Change.id.desc())
    changes = query.offset(offset).limit(limit).all()

    return [ChangeResponse.model_validate(c) for c in changes]


@router.get(
    "/changes/{change_id}",
    response_model=ChangeDetailResponse,
    summary="Get detailed view of a change including full unified diff",
)
def get_change(
    change_id: str = "",
    id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve full details of a specific change, including the unified diff.
    Enforces multi-tenant isolation via workspace ownership.
    """
    target_change_id = change_id or id
    if not target_change_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change not found or access denied",
        )

    change = (
        db.query(Change)
        .join(Workspace, Change.workspace_id == Workspace.id)
        .options(joinedload(Change.competitor), joinedload(Change.source))
        .filter(
            Change.id == target_change_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change not found or access denied",
        )

    return ChangeDetailResponse.model_validate(change)


@router.get(
    "/scans/{scan_id}/changes",
    response_model=List[ChangeResponse],
    summary="List changes detected during a specific scan run",
)
def list_scan_changes(
    scan_id: str = "",
    id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all changes detected during a specific scan run.
    Enforces multi-tenant isolation via workspace ownership of the scan run.
    """
    target_scan_id = scan_id or id
    if not target_scan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan run not found or access denied",
        )

    scan_run = (
        db.query(ScanRun)
        .join(Workspace, ScanRun.workspace_id == Workspace.id)
        .filter(
            ScanRun.id == target_scan_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not scan_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan run not found or access denied",
        )

    changes = (
        db.query(Change)
        .options(joinedload(Change.competitor), joinedload(Change.source))
        .filter(Change.scan_run_id == target_scan_id)
        .order_by(Change.detected_at.desc(), Change.id.desc())
        .all()
    )

    return [ChangeResponse.model_validate(c) for c in changes]
