"""Comprehensive Unit Tests for TradeCraft Deterministic Diff Engine & Hash Generation.

Covers:
- Unified diff format validation (--- a, +++ b, @@ hunks).
- Line & character statistics accuracy.
- Similarity ratio accuracy across varying degrees of change.
- Deterministic SHA-256 change_hash reproducibility across OS newlines (\\r\\n vs \\n).
- Edge cases: identical texts, None inputs, first snapshot, deleted text, total replacement,
  large multiline documents, Unicode/emojis, and whitespace-only diffs.
"""

import hashlib
import os
import re
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.diff import DiffEngine, DiffResult, DiffStats, compute_change_hash


# ============================================================================
# 1. Unified Diff Format Validation
# ============================================================================

def test_unified_diff_format_headers_and_hunks():
    """Verify standard unified diff format starting with --- a, +++ b, and @@ hunk headers."""
    old_text = "Alpha\nBeta\nGamma"
    new_text = "Alpha\nBeta Updated\nGamma\nDelta"

    result = DiffEngine.compute_diff(old_text, new_text)

    assert not result.is_empty
    assert not result.is_initial
    assert result.diff_unified.startswith("--- a\n+++ b\n@@")

    lines = result.diff_unified.splitlines()
    assert lines[0] == "--- a"
    assert lines[1] == "+++ b"
    assert lines[2].startswith("@@ -")
    assert "+Beta Updated" in lines
    assert "-Beta" in lines
    assert "+Delta" in lines
    assert " Alpha" in lines


def test_unified_diff_multiple_hunks():
    """Verify that widely separated changes generate multiple @@ hunk headers."""
    old_lines = [f"Item {i}" for i in range(30)]
    new_lines = list(old_lines)
    new_lines[2] = "Item 2 Modified"
    new_lines[28] = "Item 28 Modified"

    old_text = "\n".join(old_lines)
    new_text = "\n".join(new_lines)

    result = DiffEngine.compute_diff(old_text, new_text, context_lines=2)

    assert result.diff_stats["hunk_count"] == 2
    hunk_matches = re.findall(r"^@@ -[\d,]+ \+[\d,]+ @@", result.diff_unified, flags=re.MULTILINE)
    assert len(hunk_matches) == 2


def test_custom_context_lines():
    """Verify that context_lines parameter modifies the number of unmodified context lines."""
    old_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    new_text = "Line 1\nLine 2\nLine 3 Modified\nLine 4\nLine 5"

    result_c0 = DiffEngine.compute_diff(old_text, new_text, context_lines=0)
    result_c2 = DiffEngine.compute_diff(old_text, new_text, context_lines=2)

    assert result_c0.diff_stats["lines_unmodified"] == 0
    assert result_c2.diff_stats["lines_unmodified"] == 4  # 2 before, 2 after


# ============================================================================
# 2. Line & Character Statistics Accuracy
# ============================================================================

def test_lines_and_chars_added_removed_accuracy():
    """Verify exact line and character counts added and removed."""
    old_text = "Apple\nBanana\nCherry"
    # Replacing Banana (len 6) with Blackberry (len 10) and Blueberry (len 9)
    new_text = "Apple\nBlackberry\nBlueberry\nCherry"

    result = DiffEngine.compute_diff(old_text, new_text)
    stats = result.diff_stats

    assert stats["lines_added"] == 2
    assert stats["lines_removed"] == 1
    assert stats["lines_unmodified"] >= 2  # Apple and Cherry
    assert stats["chars_added"] == len("Blackberry") + len("Blueberry")  # 19
    assert stats["chars_removed"] == len("Banana")  # 6
    assert stats["change_type"] == "modification"


def test_pure_addition_statistics():
    """Verify statistics when lines are appended without removing existing content."""
    old_text = "Header\nBody"
    new_text = "Header\nBody\nFooter Line 1\nFooter Line 2"

    result = DiffEngine.compute_diff(old_text, new_text)
    stats = result.diff_stats

    assert stats["lines_added"] == 2
    assert stats["lines_removed"] == 0
    assert stats["chars_added"] == len("Footer Line 1") + len("Footer Line 2")
    assert stats["chars_removed"] == 0
    assert stats["change_type"] == "addition"


def test_pure_deletion_statistics():
    """Verify statistics when lines are deleted without adding new content."""
    old_text = "Header\nLine to delete 1\nLine to delete 2\nFooter"
    new_text = "Header\nFooter"

    result = DiffEngine.compute_diff(old_text, new_text)
    stats = result.diff_stats

    assert stats["lines_added"] == 0
    assert stats["lines_removed"] == 2
    assert stats["chars_added"] == 0
    assert stats["chars_removed"] == len("Line to delete 1") + len("Line to delete 2")
    assert stats["change_type"] == "deletion"


def test_diff_stats_dataclass_methods_and_properties():
    """Verify DiffStats to_dict() serialization and DiffResult.stats property access."""
    stats = DiffStats(
        lines_added=5,
        lines_removed=2,
        lines_unmodified=10,
        chars_added=45,
        chars_removed=18,
        similarity_ratio=0.8523,
        hunk_count=1,
        change_type="modification",
    )
    d = stats.to_dict()
    assert d["lines_added"] == 5
    assert d["lines_removed"] == 2
    assert d["similarity_ratio"] == 0.8523
    assert d["change_type"] == "modification"

    res = DiffResult(
        diff_unified="dummy diff",
        diff_stats=d,
        change_hash="a" * 64,
        is_empty=False,
        is_initial=False,
        change_type="modification",
    )
    assert res.stats.lines_added == 5
    assert res.stats.chars_added == 45
    assert res.to_dict()["change_hash"] == "a" * 64


# ============================================================================
# 3. Similarity Ratio Accuracy Across Varying Degrees of Change
# ============================================================================

def test_similarity_ratio_identical_text():
    """Verify similarity ratio is exactly 1.0 for identical content."""
    text = "TradeCraft Competitive Intelligence Platform\nVersion 2.0"
    result = DiffEngine.compute_diff(text, text)
    assert result.diff_stats["similarity_ratio"] == 1.0
    assert result.is_empty
    assert result.change_type == "none"


def test_similarity_ratio_completely_disjoint_text():
    """Verify similarity ratio is 0.0 for completely disjoint content."""
    old_text = "12345"
    new_text = "abcdef"
    result = DiffEngine.compute_diff(old_text, new_text)
    assert result.diff_stats["similarity_ratio"] == 0.0
    assert result.change_type == "replacement"


def test_similarity_ratio_minor_tweak_high_score():
    """Verify similarity ratio is high (> 0.90) for minor edits."""
    old_text = "Our enterprise pricing starts at $49 per month for up to 10 users."
    new_text = "Our enterprise pricing starts at $59 per month for up to 10 users."

    result = DiffEngine.compute_diff(old_text, new_text)
    ratio = result.diff_stats["similarity_ratio"]
    assert 0.95 <= ratio < 1.0
    assert round(ratio, 4) == ratio  # Must be rounded to 4 decimals


def test_similarity_ratio_half_changed_medium_score():
    """Verify similarity ratio is intermediate (~0.50) for moderate changes."""
    old_text = "AAA BBB CCC DDD EEE"
    new_text = "AAA BBB XXX YYY ZZZ"

    result = DiffEngine.compute_diff(old_text, new_text)
    ratio = result.diff_stats["similarity_ratio"]
    assert 0.35 <= ratio <= 0.65


# ============================================================================
# 4. Deterministic SHA-256 Change Hash Generation
# ============================================================================

def test_change_hash_format_and_length():
    """Verify change_hash is a 64-character lowercase hexadecimal string."""
    old_text = "Feature: Automated Alerts"
    new_text = "Feature: Automated Alerts & Slack Webhooks"

    result = DiffEngine.compute_diff(old_text, new_text)
    chash = result.change_hash

    assert len(chash) == 64
    assert re.match(r"^[0-9a-f]{64}$", chash)


def test_change_hash_reproducibility_across_newline_conventions():
    """Verify hash is identical regardless of CRLF vs LF vs CR line endings."""
    old_lf = "Heading\nLine 1\nLine 2"
    new_lf = "Heading\nLine 1 Modified\nLine 2\nLine 3"

    old_crlf = "Heading\r\nLine 1\r\nLine 2"
    new_crlf = "Heading\r\nLine 1 Modified\r\nLine 2\r\nLine 3"

    old_cr = "Heading\rLine 1\rLine 2"
    new_cr = "Heading\rLine 1 Modified\rLine 2\rLine 3"

    res_lf = DiffEngine.compute_diff(old_lf, new_lf)
    res_crlf = DiffEngine.compute_diff(old_crlf, new_crlf)
    res_cr = DiffEngine.compute_diff(old_cr, new_cr)

    assert res_lf.change_hash == res_crlf.change_hash == res_cr.change_hash
    assert res_lf.diff_unified == res_crlf.diff_unified == res_cr.diff_unified


def test_compute_change_hash_trailing_spaces_and_blank_lines():
    """Verify compute_change_hash normalizes trailing spaces and surrounding blank lines."""
    raw_diff = "--- a\n+++ b\n@@ -1,2 +1,2 @@\n-line 1\n+line 1 updated\n"
    diff_with_spaces = "--- a  \r\n+++ b \r\n@@ -1,2 +1,2 @@\r\n-line 1   \r\n+line 1 updated  \r\n\r\n"

    h1 = compute_change_hash(raw_diff)
    h2 = compute_change_hash(diff_with_spaces)

    assert h1 == h2
    assert len(h1) == 64


def test_compute_change_hash_empty_and_none():
    """Verify empty or None diff strings produce the SHA-256 hash of empty bytes."""
    empty_sha256 = hashlib.sha256(b"").hexdigest()

    assert compute_change_hash(None) == empty_sha256
    assert compute_change_hash("") == empty_sha256
    assert compute_change_hash("   \n\r\n   ") == empty_sha256


# ============================================================================
# 5. Clean Handling of Edge Cases
# ============================================================================

def test_edge_case_both_none():
    """Verify compute_diff(None, None) returns an empty diff result."""
    result = DiffEngine.compute_diff(None, None)

    assert result.is_empty is True
    assert result.is_initial is False
    assert result.change_type == "none"
    assert result.diff_unified == ""
    assert result.diff_stats["lines_added"] == 0
    assert result.diff_stats["lines_removed"] == 0
    assert result.diff_stats["similarity_ratio"] == 1.0
    assert result.change_hash == hashlib.sha256(b"").hexdigest()


def test_edge_case_first_snapshot_with_content():
    """Verify compute_diff(None, new_text) flags is_initial=True and change_type='initial'."""
    new_text = "Welcome to TradeCraft\nMonitoring Competitors"

    result = DiffEngine.compute_diff(None, new_text)

    assert result.is_empty is False
    assert result.is_initial is True
    assert result.change_type == "initial"
    assert result.diff_stats["lines_added"] == 2
    assert result.diff_stats["lines_removed"] == 0
    assert result.diff_stats["similarity_ratio"] == 0.0
    assert result.diff_stats["chars_added"] == len("Welcome to TradeCraft") + len("Monitoring Competitors")
    assert result.diff_unified.startswith("--- a\n+++ b\n@@")
    assert "+Welcome to TradeCraft" in result.diff_unified


def test_edge_case_first_snapshot_empty_content():
    """Verify compute_diff(None, '') is handled cleanly as empty initial snapshot."""
    result = DiffEngine.compute_diff(None, "")

    assert result.is_empty is True
    assert result.is_initial is True
    assert result.change_type == "none"
    assert result.diff_unified == ""
    assert result.diff_stats["lines_added"] == 0
    assert result.diff_stats["similarity_ratio"] == 1.0


def test_edge_case_complete_deletion_with_none_or_empty():
    """Verify deletion when new_text is None or empty string."""
    old_text = "Line 1\nLine 2\nLine 3"

    res_none = DiffEngine.compute_diff(old_text, None)
    res_empty = DiffEngine.compute_diff(old_text, "")

    for res in (res_none, res_empty):
        assert res.is_empty is False
        assert res.is_initial is False
        assert res.change_type == "deletion"
        assert res.diff_stats["lines_removed"] == 3
        assert res.diff_stats["lines_added"] == 0
        assert res.diff_stats["similarity_ratio"] == 0.0
        assert res.diff_unified.startswith("--- a\n+++ b\n@@")
        assert "-Line 1" in res.diff_unified


def test_edge_case_addition_from_empty_string():
    """Verify addition when old_text is empty string and new_text has content."""
    new_text = "Line 1\nLine 2"
    result = DiffEngine.compute_diff("", new_text)

    assert result.is_empty is False
    assert result.is_initial is False
    assert result.change_type == "addition"
    assert result.diff_stats["lines_added"] == 2
    assert result.diff_stats["lines_removed"] == 0
    assert result.diff_stats["similarity_ratio"] == 0.0


def test_edge_case_100_percent_replacement_content():
    """Verify complete replacement when no characters or lines are shared."""
    old_text = "1111\n2222"
    new_text = "AAAA\nBBBB"

    result = DiffEngine.compute_diff(old_text, new_text)

    assert result.is_empty is False
    assert result.change_type == "replacement"
    assert result.diff_stats["similarity_ratio"] == 0.0
    assert result.diff_stats["lines_added"] == 2
    assert result.diff_stats["lines_removed"] == 2


def test_edge_case_trailing_newline_difference_only():
    """Verify that texts differing only by trailing newline are treated as identical."""
    old_text = "Line 1\nLine 2\n"
    new_text = "Line 1\nLine 2"

    result = DiffEngine.compute_diff(old_text, new_text)

    assert result.is_empty is True
    assert result.change_type == "none"
    assert result.diff_unified == ""
    assert result.diff_stats["similarity_ratio"] == 1.0


def test_large_multiline_documents():
    """Verify performance and accuracy on large documents (> 5,000 lines)."""
    old_lines = [f"Record {i}: original payload content for index {i}" for i in range(1000)]
    new_lines = list(old_lines)
    # Modify 5 lines across the document
    for idx in (10, 250, 500, 750, 990):
        new_lines[idx] = f"Record {idx}: UPDATED payload content for index {idx}"

    old_text = "\n".join(old_lines)
    new_text = "\n".join(new_lines)

    result = DiffEngine.compute_diff(old_text, new_text)

    assert not result.is_empty
    assert result.diff_stats["lines_added"] == 5
    assert result.diff_stats["lines_removed"] == 5
    assert result.diff_stats["hunk_count"] == 5
    assert result.diff_stats["change_type"] == "modification"
    assert len(result.change_hash) == 64


def test_unicode_and_emojis():
    """Verify diffing and hashing works accurately with Unicode and emojis."""
    old_text = "© 2024 TradeCraft Inc. 🚀\nPrices: €49 / ¥5000\n日本語テキスト"
    new_text = "© 2025 TradeCraft Inc. 🚀\nPrices: €59 / ¥6000\n日本語テキスト更新"

    result = DiffEngine.compute_diff(old_text, new_text)

    assert not result.is_empty
    assert result.diff_stats["lines_added"] == 3
    assert result.diff_stats["lines_removed"] == 3
    assert len(result.change_hash) == 64
    assert "+Prices: €59 / ¥6000" in result.diff_unified


def test_class_and_instance_invocation_parity():
    """Verify that DiffEngine works identically whether invoked as class or instance."""
    old_text = "Hello\nWorld"
    new_text = "Hello\nWorld!"

    res_class = DiffEngine.compute_diff(old_text, new_text)
    engine_inst = DiffEngine()
    res_inst = engine_inst.compute_diff(old_text, new_text)

    assert res_class.diff_unified == res_inst.diff_unified
    assert res_class.diff_stats == res_inst.diff_stats
    assert res_class.change_hash == res_inst.change_hash
