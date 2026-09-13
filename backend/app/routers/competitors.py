# backend/app/routers/competitors.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.schemas.competitor import CompetitorCreate, CompetitorUpdate, CompetitorResponse
from app.dependencies.auth import get_current_user

router = APIRouter(tags=["Competitors"])

def get_user_workspace(workspace_id: str, user_id: str, db: Session) -> Workspace:
    """Helper to verify workspace exists and belongs to current user."""
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == user_id,
    ).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied",
        )
    return workspace


@router.post("/workspaces/{workspace_id}/competitors", response_model=CompetitorResponse, status_code=status.HTTP_201_CREATED)
def create_competitor(
    workspace_id: str,
    comp_in: CompetitorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new competitor within a workspace.
    """
    get_user_workspace(workspace_id, current_user.id, db)
    
    competitor = Competitor(
        workspace_id=workspace_id,
        name=comp_in.name,
        description=comp_in.description,
        website=str(comp_in.website) if comp_in.website else None,
        monitoring_enabled=comp_in.monitoring_enabled,
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    
    resp = CompetitorResponse.model_validate(competitor)
    resp.source_count = 0
    return resp


@router.get("/workspaces/{workspace_id}/competitors", response_model=List[CompetitorResponse])
def list_competitors(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all competitors inside a workspace.
    """
    get_user_workspace(workspace_id, current_user.id, db)
    
    competitors = db.query(Competitor).filter(
        Competitor.workspace_id == workspace_id
    ).order_by(Competitor.created_at.desc()).all()
    
    result = []
    for comp in competitors:
        source_count = db.query(Source).filter(Source.competitor_id == comp.id).count()
        item = CompetitorResponse.model_validate(comp)
        item.source_count = source_count
        result.append(item)
        
    return result


@router.get("/workspaces/{workspace_id}/competitors/{competitor_id}", response_model=CompetitorResponse)
def get_competitor(
    workspace_id: str,
    competitor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single competitor by ID inside a workspace.
    """
    get_user_workspace(workspace_id, current_user.id, db)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.workspace_id == workspace_id,
    ).first()
    
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found inside workspace",
        )
        
    source_count = db.query(Source).filter(Source.competitor_id == competitor.id).count()
    resp = CompetitorResponse.model_validate(competitor)
    resp.source_count = source_count
    return resp


@router.put("/workspaces/{workspace_id}/competitors/{competitor_id}", response_model=CompetitorResponse)
def update_competitor(
    workspace_id: str,
    competitor_id: str,
    comp_in: CompetitorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update competitor information.
    """
    get_user_workspace(workspace_id, current_user.id, db)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.workspace_id == workspace_id,
    ).first()
    
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found inside workspace",
        )
        
    if comp_in.name is not None:
        competitor.name = comp_in.name
    if comp_in.description is not None:
        competitor.description = comp_in.description
    if comp_in.website is not None:
        competitor.website = str(comp_in.website)
    if comp_in.monitoring_enabled is not None:
        competitor.monitoring_enabled = comp_in.monitoring_enabled
        
    db.commit()
    db.refresh(competitor)
    
    source_count = db.query(Source).filter(Source.competitor_id == competitor.id).count()
    resp = CompetitorResponse.model_validate(competitor)
    resp.source_count = source_count
    return resp


@router.delete("/workspaces/{workspace_id}/competitors/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor(
    workspace_id: str,
    competitor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a competitor and its configured sources.
    """
    get_user_workspace(workspace_id, current_user.id, db)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.workspace_id == workspace_id,
    ).first()
    
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found inside workspace",
        )
        
    db.delete(competitor)
    db.commit()
    return None
