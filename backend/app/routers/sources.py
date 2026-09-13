# backend/app/routers/sources.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse, VALID_SOURCE_TYPES
from app.dependencies.auth import get_current_user

router = APIRouter(tags=["Sources"])

def get_user_competitor(competitor_id: str, user_id: str, db: Session) -> Competitor:
    """Helper to verify competitor exists and belongs to a workspace owned by current user."""
    competitor = (
        db.query(Competitor)
        .join(Workspace, Competitor.workspace_id == Workspace.id)
        .filter(Competitor.id == competitor_id, Workspace.user_id == user_id)
        .first()
    )
    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found or access denied",
        )
    return competitor


@router.post("/competitors/{competitor_id}/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    competitor_id: str,
    source_in: SourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new source configuration for a competitor.
    """
    get_user_competitor(competitor_id, current_user.id, db)
    
    stype = source_in.source_type.lower()
    if stype not in VALID_SOURCE_TYPES:
        stype = "website"
        
    source = Source(
        competitor_id=competitor_id,
        name=source_in.name,
        url=str(source_in.url),
        source_type=stype,
        monitoring_enabled=source_in.monitoring_enabled,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    
    return SourceResponse.model_validate(source)


@router.get("/competitors/{competitor_id}/sources", response_model=List[SourceResponse])
def list_sources(
    competitor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all configured sources for a competitor.
    """
    get_user_competitor(competitor_id, current_user.id, db)
    
    sources = db.query(Source).filter(
        Source.competitor_id == competitor_id
    ).order_by(Source.created_at.desc()).all()
    
    return [SourceResponse.model_validate(s) for s in sources]


@router.get("/competitors/{competitor_id}/sources/{source_id}", response_model=SourceResponse)
def get_source(
    competitor_id: str,
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single source by ID.
    """
    get_user_competitor(competitor_id, current_user.id, db)
    
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.competitor_id == competitor_id,
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found for this competitor",
        )
        
    return SourceResponse.model_validate(source)


@router.put("/competitors/{competitor_id}/sources/{source_id}", response_model=SourceResponse)
def update_source(
    competitor_id: str,
    source_id: str,
    source_in: SourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a source configuration.
    """
    get_user_competitor(competitor_id, current_user.id, db)
    
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.competitor_id == competitor_id,
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found for this competitor",
        )
        
    if source_in.name is not None:
        source.name = source_in.name
    if source_in.url is not None:
        source.url = str(source_in.url)
    if source_in.source_type is not None:
        stype = source_in.source_type.lower()
        if stype in VALID_SOURCE_TYPES:
            source.source_type = stype
    if source_in.monitoring_enabled is not None:
        source.monitoring_enabled = source_in.monitoring_enabled
        
    db.commit()
    db.refresh(source)
    
    return SourceResponse.model_validate(source)


@router.delete("/competitors/{competitor_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    competitor_id: str,
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a source configuration.
    """
    get_user_competitor(competitor_id, current_user.id, db)
    
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.competitor_id == competitor_id,
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found for this competitor",
        )
        
    db.delete(source)
    db.commit()
    return None
