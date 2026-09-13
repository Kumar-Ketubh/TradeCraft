# backend/db.py
#
# TradeCraft — Database Connection Helper (Phase 1)
#
# PURPOSE:
#   Provide a single function to test PostgreSQL reachability.
#   Used only by the /health endpoint in Phase 1.
#
# IMPORTANT:
#   All connection parameters are read from environment variables.
#   Never hardcode credentials here.
#   Copy .env.example to .env and fill in your values.
#
# FUTURE:
#   Phase 2+ will add a proper connection pool and ORM/query layer.
#   This file is intentionally minimal for Phase 1.

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def check_db_connection() -> tuple[bool, str]:
    """
    Attempt a lightweight connection to PostgreSQL.

    Returns:
        (True, "Connected") on success
        (False, <error message>) on failure
    """
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "tradecraft")
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")

    if not user:
        return False, "DB_USER environment variable not set"

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=name,
            user=user,
            password=password,
            connect_timeout=3,
        )
        conn.close()
        return True, "Connected"
    except psycopg2.OperationalError as e:
        return False, str(e).strip()
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
