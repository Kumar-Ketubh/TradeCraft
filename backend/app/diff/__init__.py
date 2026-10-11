"""TradeCraft Deterministic Diff Engine & Hash Generation Package."""

try:
    from app.diff.engine import (
        DiffEngine,
        DiffResult,
        DiffStats,
        compute_change_hash,
    )
except ImportError:  # Fallback when imported via backend.app...
    from backend.app.diff.engine import (
        DiffEngine,
        DiffResult,
        DiffStats,
        compute_change_hash,
    )

__all__ = [
    "DiffEngine",
    "DiffResult",
    "DiffStats",
    "compute_change_hash",
]
