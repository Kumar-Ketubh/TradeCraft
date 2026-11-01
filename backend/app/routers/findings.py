# backend/app/routers/findings.py
"""
Intelligence findings router for TradeCraft competitive intelligence.

Provides endpoints for querying AI-analyzed findings, evidence quotes,
triggering agent analysis on detected changes, and managing verification status.
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.change import Change
from app.models.user import User
from app.models.workspace import Workspace
from app.models.finding import (
    IntelligenceFinding,
    FindingCategory,
    ConfidenceLevel,
    VerificationStatus,
)
from app.schemas.finding import FindingResponse
from app.services.agents.graph import run_agent_pipeline

router = APIRouter(tags=["Findings"])


def _verify_workspace_access(workspace_id: str, user_id: str, db: Session) -> Workspace:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.user_id == user_id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )
    return workspace


@router.get(
    "/workspaces/{workspace_id}/findings",
    response_model=List[FindingResponse],
    summary="List intelligence findings for a workspace",
)
def list_findings(
    workspace_id: str,
    category: Optional[FindingCategory] = None,
    confidence_level: Optional[ConfidenceLevel] = None,
    verification_status: Optional[VerificationStatus] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List intelligence findings for a workspace with evidence quotes and filters."""
    _verify_workspace_access(workspace_id, current_user.id, db)

    query = (
        db.query(IntelligenceFinding)
        .options(
            joinedload(IntelligenceFinding.evidence_quotes),
            joinedload(IntelligenceFinding.change),
        )
        .filter(IntelligenceFinding.workspace_id == workspace_id)
    )

    if category:
        query = query.filter(IntelligenceFinding.category == category.value)
    if confidence_level:
        query = query.filter(IntelligenceFinding.confidence_level == confidence_level.value)
    if verification_status:
        query = query.filter(IntelligenceFinding.verification_status == verification_status.value)

    findings = (
        query.order_by(IntelligenceFinding.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return findings


@router.get(
    "/findings/{finding_id}",
    response_model=FindingResponse,
    summary="Retrieve a detailed finding with grounded evidence quotes",
)
def get_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed finding and all associated snapshot evidence quotes."""
    finding = (
        db.query(IntelligenceFinding)
        .options(
            joinedload(IntelligenceFinding.evidence_quotes),
            joinedload(IntelligenceFinding.change),
        )
        .join(Workspace, IntelligenceFinding.workspace_id == Workspace.id)
        .filter(
            IntelligenceFinding.id == finding_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found or unauthorized access",
        )
    return finding


@router.patch(
    "/findings/{finding_id}/status",
    response_model=FindingResponse,
    summary="Update finding verification status",
)
def update_finding_status(
    finding_id: str,
    status_update: VerificationStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually update or override a finding's verification status."""
    finding = (
        db.query(IntelligenceFinding)
        .options(joinedload(IntelligenceFinding.evidence_quotes))
        .join(Workspace, IntelligenceFinding.workspace_id == Workspace.id)
        .filter(
            IntelligenceFinding.id == finding_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found or unauthorized access",
        )

    finding.verification_status = status_update.value
    db.commit()
    db.refresh(finding)
    return finding


@router.post(
    "/changes/{change_id}/analyze",
    response_model=FindingResponse,
    summary="Trigger AI agent analysis on a detected change",
)
def analyze_change(
    change_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes the LangGraph competitive intelligence pipeline on a detected change.
    Returns the verified finding with character-level evidence grounding.
    """
    change = (
        db.query(Change)
        .join(Workspace, Change.workspace_id == Workspace.id)
        .filter(
            Change.id == change_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change not found or unauthorized access",
        )

    finding = run_agent_pipeline(change_id=change.id, db=db)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent pipeline failed to produce finding.",
        )

    return finding
