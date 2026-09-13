# backend/main.py
#
# TradeCraft API Backend — Phase 2: Core Management
# FastAPI + PostgreSQL (SQLAlchemy) + JWT Authentication

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.database import create_db_engine, Base
from app.routers import auth, workspaces, competitors, sources
from db import check_db_connection

# Ensure tables are created if database is reachable
try:
    engine = create_db_engine()
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[TradeCraft Backend] Warning: DB creation on startup skipped ({e})")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TradeCraft Phase 2 Backend — Auth, Workspaces, Competitors & Sources",
    version=settings.VERSION,
)

# CORS — open for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Phase 2 Modular Routers
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(competitors.router)
app.include_router(sources.router)


@app.get("/health", summary="Health check")
def health():
    """
    Returns current health status of FastAPI backend and PostgreSQL database.
    """
    db_ok = False
    db_msg = ""
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
        db_msg = "Connected"
    except Exception as e:
        db_ok, db_msg = check_db_connection()

    return {
        "backend": "ok",
        "database": "ok" if db_ok else "error",
        "database_message": db_msg,
        "ai_workflow": "not_connected",
        "phase": settings.PHASE,
    }
