# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.auth import UserRegister, UserLogin, UserResponse, Token, GoogleLogin
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account and auto-create a default workspace for them.
    """
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )
    
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        name=user_in.name,
        email=user_in.email.lower(),
        password_hash=hashed_pwd,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default initial workspace for seamless UX
    default_ws = Workspace(
        name=f"{user.name.split()[0]}'s Workspace",
        user_id=user.id,
    )
    db.add(default_ws)
    db.commit()

    token = create_access_token(subject=user.id)
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token.
    """
    user = db.query(User).filter(User.email == credentials.email.lower()).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    token = create_access_token(subject=user.id)
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/google", response_model=Token)
def google_login(payload: GoogleLogin, db: Session = Depends(get_db)):
    """
    Authenticate user using Google ID token, and return JWT access token.
    Auto-registers new users.
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email = idinfo["email"].lower()
        name = idinfo.get("name", email.split("@")[0])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google token",
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create new user without password (or dummy password since auth relies on Google)
        import secrets
        dummy_pwd = get_password_hash(secrets.token_urlsafe(32))
        user = User(
            name=name,
            email=email,
            password_hash=dummy_pwd,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create default initial workspace for seamless UX
        default_ws = Workspace(
            name=f"{user.name.split()[0]}'s Workspace",
            user_id=user.id,
        )
        db.add(default_ws)
        db.commit()
    
    token = create_access_token(subject=user.id)
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve profile details of the currently authenticated user.
    """
    return current_user
