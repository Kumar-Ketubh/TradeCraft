"""TradeCraft Deterministic Unified Diff Engine & Hash Generation.

This module provides line-by-line unified diff calculation, exact diff statistics
(lines/chars added and removed, unmodified context lines, hunk count, SequenceMatcher
similarity ratio), deterministic 64-character lowercase SHA-256 hash generation invariant
to OS newline differences and trailing whitespace, and robust handling of all edge cases
including initial snapshots, complete deletions, total replacements, and empty diffs.
"""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DiffStats:
    """Statistics summarizing differences between two text documents."""

    lines_added: int
    lines_removed: int
    lines_unmodified: int
    chars_added: int
    chars_removed: int
    similarity_ratio: float
    hunk_count: int
    change_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to a serializable dictionary."""
        return {
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "lines_unmodified": self.lines_unmodified,
            "chars_added": self.chars_added,
            "chars_removed": self.chars_removed,
            "similarity_ratio": self.similarity_ratio,
            "hunk_count": self.hunk_count,
            "change_type": self.change_type,
        }


@dataclass(frozen=True)
class DiffResult:
    """Result of computing a unified diff between two text documents."""

    diff_unified: str
    diff_stats: Dict[str, Any]
    change_hash: str
    is_empty: bool
    is_initial: bool
    change_type: str

    @property
    def stats(self) -> DiffStats:
        """Typed accessor for diff statistics."""
        return DiffStats(
            lines_added=self.diff_stats.get("lines_added", 0),
            lines_removed=self.diff_stats.get("lines_removed", 0),
            lines_unmodified=self.diff_stats.get("lines_unmodified", 0),
            chars_added=self.diff_stats.get("chars_added", 0),
            chars_removed=self.diff_stats.get("chars_removed", 0),
            similarity_ratio=self.diff_stats.get("similarity_ratio", 0.0),
            hunk_count=self.diff_stats.get("hunk_count", 0),
            change_type=self.diff_stats.get("change_type", self.change_type),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert diff result to a serializable dictionary."""
        return {
            "diff_unified": self.diff_unified,
            "diff_stats": self.diff_stats,
            "change_hash": self.change_hash,
            "is_empty": self.is_empty,
            "is_initial": self.is_initial,
            "change_type": self.change_type,
        }


def compute_change_hash(diff_unified: Optional[str]) -> str:
    """Compute a deterministic 64-char lowercase SHA-256 hash of a unified diff.

    Normalizes line endings (\\r\\n and \\r -> \\n), strips trailing whitespace
    per line, and strips leading/trailing blank lines before hashing.
    Empty or whitespace-only diffs return the SHA-256 hash of empty bytes.
    """
    if not diff_unified:
        return hashlib.sha256(b"").hexdigest().lower()

    lines = [line.rstrip() for line in diff_unified.splitlines()]
    normalized = "\n".join(lines).strip()
    if not normalized:
        return hashlib.sha256(b"").hexdigest().lower()

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().lower()


class DiffEngine:
    """Deterministic diff engine for computing unified diffs and statistics."""

    @classmethod
    def compute_diff(
        cls,
        old_text: Optional[str],
        new_text: Optional[str],
        context_lines: int = 3,
    ) -> DiffResult:
        """Compute line-by-line unified diff and exact statistics.

        Parameters
        ----------
        old_text : Optional[str]
            Prior document content, or None if this is the first snapshot.
        new_text : Optional[str]
            Current document content, or None/empty if deleted.
        context_lines : int, default 3
            Number of context lines surrounding diff hunks.

        Returns
        -------
        DiffResult
            Unified diff string, dictionary of diff stats, deterministic SHA-256 hash,
            empty flag, initial flag, and change type.
        """
        # Case 1: Both old and new text are None
        if old_text is None and new_text is None:
            stats = DiffStats(
                lines_added=0,
                lines_removed=0,
                lines_unmodified=0,
                chars_added=0,
                chars_removed=0,
                similarity_ratio=1.0,
                hunk_count=0,
                change_type="none",
            )
            return DiffResult(
                diff_unified="",
                diff_stats=stats.to_dict(),
                change_hash=compute_change_hash(""),
                is_empty=True,
                is_initial=False,
                change_type="none",
            )

        # Case 2: First snapshot (old_text is None)
        if old_text is None:
            if not new_text:
                # Initial snapshot with empty content
                stats = DiffStats(
                    lines_added=0,
                    lines_removed=0,
                    lines_unmodified=0,
                    chars_added=0,
                    chars_removed=0,
                    similarity_ratio=1.0,
                    hunk_count=0,
                    change_type="none",
                )
                return DiffResult(
                    diff_unified="",
                    diff_stats=stats.to_dict(),
                    change_hash=compute_change_hash(""),
                    is_empty=True,
                    is_initial=True,
                    change_type="none",
                )

            lines_new = new_text.splitlines()
            diff_lines = list(
                difflib.unified_diff(
                    [],
                    lines_new,
                    fromfile="a",
                    tofile="b",
                    lineterm="",
                    n=context_lines,
                )
            )
            diff_unified = "\n".join(diff_lines)
            lines_added = len(lines_new)
            chars_added = sum(len(line) for line in lines_new)
            hunk_count = sum(1 for line in diff_lines if line.startswith("@@"))
            stats = DiffStats(
                lines_added=lines_added,
                lines_removed=0,
                lines_unmodified=0,
                chars_added=chars_added,
                chars_removed=0,
                similarity_ratio=0.0,
                hunk_count=hunk_count,
                change_type="initial",
            )
            return DiffResult(
                diff_unified=diff_unified,
                diff_stats=stats.to_dict(),
                change_hash=compute_change_hash(diff_unified),
                is_empty=False,
                is_initial=True,
                change_type="initial",
            )

        # Case 3: Identical texts
        if old_text == new_text:
            stats = DiffStats(
                lines_added=0,
                lines_removed=0,
                lines_unmodified=0,
                chars_added=0,
                chars_removed=0,
                similarity_ratio=1.0,
                hunk_count=0,
                change_type="none",
            )
            return DiffResult(
                diff_unified="",
                diff_stats=stats.to_dict(),
                change_hash=compute_change_hash(""),
                is_empty=True,
                is_initial=False,
                change_type="none",
            )

        # Case 4: Complete deletion (new_text is None or empty, while old_text had content)
        if (new_text is None or new_text == "") and old_text:
            lines_old = old_text.splitlines()
            diff_lines = list(
                difflib.unified_diff(
                    lines_old,
                    [],
                    fromfile="a",
                    tofile="b",
                    lineterm="",
                    n=context_lines,
                )
            )
            diff_unified = "\n".join(diff_lines)
            lines_removed = len(lines_old)
            chars_removed = sum(len(line) for line in lines_old)
            hunk_count = sum(1 for line in diff_lines if line.startswith("@@"))
            stats = DiffStats(
                lines_added=0,
                lines_removed=lines_removed,
                lines_unmodified=0,
                chars_added=0,
                chars_removed=chars_removed,
                similarity_ratio=0.0,
                hunk_count=hunk_count,
                change_type="deletion",
            )
            return DiffResult(
                diff_unified=diff_unified,
                diff_stats=stats.to_dict(),
                change_hash=compute_change_hash(diff_unified),
                is_empty=False,
                is_initial=False,
                change_type="deletion",
            )

        # Case 5: Empty old_text mutated to non-empty new_text
        if old_text == "" and new_text:
            lines_new = new_text.splitlines()
            diff_lines = list(
                difflib.unified_diff(
                    [],
                    lines_new,
                    fromfile="a",
                    tofile="b",
                    lineterm="",
                    n=context_lines,
                )
            )
            diff_unified = "\n".join(diff_lines)
            lines_added = len(lines_new)
            chars_added = sum(len(line) for line in lines_new)
            hunk_count = sum(1 for line in diff_lines if line.startswith("@@"))
            stats = DiffStats(
                lines_added=lines_added,
                lines_removed=0,
                lines_unmodified=0,
                chars_added=chars_added,
                chars_removed=0,
                similarity_ratio=0.0,
                hunk_count=hunk_count,
                change_type="addition",
            )
            return DiffResult(
                diff_unified=diff_unified,
                diff_stats=stats.to_dict(),
                change_hash=compute_change_hash(diff_unified),
                is_empty=False,
                is_initial=False,
                change_type="addition",
            )

        # Case 6: General mutation between two non-empty strings
        lines_old = old_text.splitlines()
        lines_new = new_text.splitlines()
        diff_lines = list(
            difflib.unified_diff(
                lines_old,
                lines_new,
                fromfile="a",
                tofile="b",
                lineterm="",
                n=context_lines,
            )
        )

        if not diff_lines:
            # Texts only differed by trailing newlines or splits produced identical lines
            stats = DiffStats(
                lines_added=0,
                lines_removed=0,
                lines_unmodified=0,
                chars_added=0,
                chars_removed=0,
                similarity_ratio=1.0,
                hunk_count=0,
                change_type="none",
            )
            return DiffResult(
                diff_unified="",
                diff_stats=stats.to_dict(),
                change_hash=compute_change_hash(""),
                is_empty=True,
                is_initial=False,
                change_type="none",
            )

        diff_unified = "\n".join(diff_lines)
        lines_added = sum(
            1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
        )
        lines_removed = sum(
            1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
        )
        lines_unmodified = sum(1 for line in diff_lines if line.startswith(" "))
        chars_added = sum(
            len(line[1:]) for line in diff_lines if line.startswith("+") and not line.startswith("+++")
        )
        chars_removed = sum(
            len(line[1:]) for line in diff_lines if line.startswith("-") and not line.startswith("---")
        )
        hunk_count = sum(1 for line in diff_lines if line.startswith("@@"))

        # Similarity ratio calculation: use line SequenceMatcher for very large texts to avoid O(N^2)
        non_ws_old = "".join(old_text.split())
        non_ws_new = "".join(new_text.split())
        if non_ws_old and non_ws_new and difflib.SequenceMatcher(None, non_ws_old, non_ws_new).ratio() == 0.0:
            raw_ratio = 0.0
        elif len(old_text) > 25000 or len(new_text) > 25000:
            raw_ratio = difflib.SequenceMatcher(None, lines_old, lines_new).ratio()
        else:
            raw_ratio = difflib.SequenceMatcher(None, old_text, new_text).ratio()
        similarity_ratio = round(raw_ratio, 4)

        # Determine change type
        if lines_removed == 0 and lines_added > 0:
            change_type = "addition"
        elif lines_added == 0 and lines_removed > 0:
            change_type = "deletion"
        elif similarity_ratio == 0.0:
            change_type = "replacement"
        else:
            change_type = "modification"

        stats = DiffStats(
            lines_added=lines_added,
            lines_removed=lines_removed,
            lines_unmodified=lines_unmodified,
            chars_added=chars_added,
            chars_removed=chars_removed,
            similarity_ratio=similarity_ratio,
            hunk_count=hunk_count,
            change_type=change_type,
        )

        return DiffResult(
            diff_unified=diff_unified,
            diff_stats=stats.to_dict(),
            change_hash=compute_change_hash(diff_unified),
            is_empty=False,
            is_initial=False,
            change_type=change_type,
        )
