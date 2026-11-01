# backend/app/routers/proposals.py
"""
Proposals router for TradeCraft competitive intelligence.

Provides endpoints for synthesizing, retrieving, updating, and managing
structured, evidence-grounded strategic counter-proposals.
"""

from __future__ import annotations

from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.proposal import Proposal, ProposalStatus
from app.models.finding import IntelligenceFinding, VerificationStatus
from app.schemas.proposal import ProposalCreate, ProposalUpdate, ProposalResponse
from app.services.proposal_engine.generator import generate_structured_proposal

router = APIRouter(tags=["Proposals"])


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
    "/workspaces/{workspace_id}/proposals",
    response_model=List[ProposalResponse],
    summary="List all proposals in a workspace",
)
def list_proposals(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all proposals generated for a workspace."""
    _verify_workspace_access(workspace_id, current_user.id, db)

    proposals = (
        db.query(Proposal)
        .filter(Proposal.workspace_id == workspace_id)
        .order_by(Proposal.created_at.desc())
        .all()
    )
    return proposals


@router.post(
    "/workspaces/{workspace_id}/proposals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and save a structured counter-proposal",
)
def create_proposal(
    workspace_id: str,
    proposal_in: ProposalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Synthesizes and persists a structured project proposal using verified findings.
    Enforces strict grounding: rejects any unverified or rejected findings.
    """
    workspace = _verify_workspace_access(workspace_id, current_user.id, db)

    findings: List[IntelligenceFinding] = []
    if proposal_in.finding_ids:
        findings = (
            db.query(IntelligenceFinding)
            .options(joinedload(IntelligenceFinding.evidence_quotes))
            .filter(
                IntelligenceFinding.id.in_(proposal_in.finding_ids),
                IntelligenceFinding.workspace_id == workspace_id,
            )
            .all()
        )

        if len(findings) != len(proposal_in.finding_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more specified findings were not found in this workspace.",
            )

        # STRICT VALIDATION: Reject any unverified or rejected finding
        unverified = [f for f in findings if f.verification_status != VerificationStatus.VERIFIED.value]
        if unverified:
            unverified_info = [f"'{f.title}' ({f.verification_status})" for f in unverified]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot generate proposal with unverified findings: {', '.join(unverified_info)}. Only VERIFIED findings may be used.",
            )

    # Determine markdown content
    content = proposal_in.markdown_content
    if not content or not content.strip():
        try:
            content = generate_structured_proposal(
                workspace=workspace,
                findings=findings,
                title=proposal_in.title,
                target_goal=proposal_in.target_goal or "",
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    proposal = Proposal(
        workspace_id=workspace_id,
        title=proposal_in.title,
        target_goal=proposal_in.target_goal,
        markdown_content=content,
        status=ProposalStatus.DRAFT.value,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalResponse,
    summary="Retrieve proposal by ID",
)
def get_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve proposal by ID with workspace ownership verification."""
    proposal = (
        db.query(Proposal)
        .join(Workspace, Proposal.workspace_id == Workspace.id)
        .filter(
            Proposal.id == proposal_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found or unauthorized access",
        )
    return proposal


@router.put(
    "/proposals/{proposal_id}",
    response_model=ProposalResponse,
    summary="Update proposal content or status",
)
def update_proposal(
    proposal_id: str,
    update_in: ProposalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update proposal title, target goal, markdown content, or status."""
    proposal = (
        db.query(Proposal)
        .join(Workspace, Proposal.workspace_id == Workspace.id)
        .filter(
            Proposal.id == proposal_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found or unauthorized access",
        )

    update_data = update_in.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value

    for field, val in update_data.items():
        setattr(proposal, field, val)

    proposal.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.delete(
    "/proposals/{proposal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete proposal",
)
def delete_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a proposal."""
    proposal = (
        db.query(Proposal)
        .join(Workspace, Proposal.workspace_id == Workspace.id)
        .filter(
            Proposal.id == proposal_id,
            Workspace.user_id == current_user.id,
        )
        .first()
    )
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found or unauthorized access",
        )

    db.delete(proposal)
    db.commit()
    return None
