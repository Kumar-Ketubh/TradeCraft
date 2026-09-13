# backend/app/db/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

def create_db_engine(url: str = None):
    db_url = url or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

Base = declarative_base()

def get_db():
    """FastAPI dependency yielding a database session per request."""
    db_engine = create_db_engine()
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
