# backend/app/db/database.py
import os
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection) or type(dbapi_connection).__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_engine(url: str = None):
    db_url = url or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if not db_url:
        db_url = "sqlite:///./tradecraft.db"

    # Supabase and other cloud providers often provide URLs starting with postgres://
    # SQLAlchemy requires postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )

    # PostgreSQL / Supabase
    connect_args = {}
    if "supabase.co" in db_url or "pooler.supabase.com" in db_url:
        connect_args["sslmode"] = "require"

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args,
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
