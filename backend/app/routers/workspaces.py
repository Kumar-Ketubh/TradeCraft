# backend/app/routers/workspaces.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    ws_in: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new workspace owned by the current user.
    """
    workspace = Workspace(
        name=ws_in.name,
        user_id=current_user.id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    resp = WorkspaceResponse.model_validate(workspace)
    resp.competitor_count = 0
    return resp


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all workspaces belonging to the authenticated user.
    """
    workspaces = db.query(Workspace).filter(Workspace.user_id == current_user.id).order_by(Workspace.created_at.desc()).all()
    
    result = []
    for ws in workspaces:
        comp_count = db.query(Competitor).filter(Competitor.workspace_id == ws.id).count()
        item = WorkspaceResponse.model_validate(ws)
        item.competitor_count = comp_count
        result.append(item)
        
    return result


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get single workspace details by ID (must be owned by current user).
    """
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id,
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )
        
    comp_count = db.query(Competitor).filter(Competitor.workspace_id == workspace.id).count()
    resp = WorkspaceResponse.model_validate(workspace)
    resp.competitor_count = comp_count
    return resp


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: str,
    ws_in: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update workspace details (must be owned by current user).
    """
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id,
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )
        
    if ws_in.name is not None:
        workspace.name = ws_in.name
        
    db.commit()
    db.refresh(workspace)
    
    comp_count = db.query(Competitor).filter(Competitor.workspace_id == workspace.id).count()
    resp = WorkspaceResponse.model_validate(workspace)
    resp.competitor_count = comp_count
    return resp


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a workspace and all associated competitors and sources.
    """
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id,
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or unauthorized access",
        )
        
    db.delete(workspace)
    db.commit()
    return None
