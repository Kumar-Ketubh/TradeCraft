"""
Meaningfulness and domain categorization classifier for snapshot diffs.

Provides deterministic heuristic and regex-based classification without
external LLM dependencies. Filters cosmetic and web scraping noise
(whitespace, punctuation, copyright year roll-forward, cookie/GDPR banners,
CSRF tokens, session IDs, build/commit hashes) and categorizes substantive changes
into domain categories (pricing_change, feature_announcement, positioning_shift,
documentation_update, blog_post, unknown).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import difflib
import re
from typing import Any, Dict, List, Optional, Tuple


# Base significance scores per category
BASE_SCORES: Dict[str, float] = {
    "pricing_change": 0.90,
    "feature_announcement": 0.85,
    "positioning_shift": 0.75,
    "documentation_update": 0.65,
    "blog_post": 0.60,
    "unknown": 0.40,
    "noise": 0.00,
}

# Regex pattern for copyright roll-forward detection
COPYRIGHT_RE = re.compile(
    r"(?:©|&copy;|\(c\)|copyright)\s*(?:(?:\d{4}\s*[-–—]\s*)?\b(20\d\d)\b)",
    re.IGNORECASE,
)

# Regex patterns for noise detection
COOKIE_GDPR_RE = re.compile(
    r"\b(?:cookie|cookies|cookie\s+policy|consent|gdpr|tracking\s+consent|privacy\s+preferences|manage\s+cookies|accept\s+all\s+cookies|decline\s+cookies|privacy\s+settings)\b",
    re.IGNORECASE,
)

TOKEN_CSRF_RE = re.compile(
    r"\b(?:csrf[_-]?token|authenticity[_-]?token|nonce|auth[_-]?token|_csrf|__cf_bm|cf-ray|cf-cache-status|x-request-id)\b",
    re.IGNORECASE,
)

SESSION_TRACE_RE = re.compile(
    r"\b(?:session[_-]?id|request[_-]?id|trace[_-]?id|rendered\s+in\s+[\d.]+\s*(?:s|ms)|server\s+timestamp|generated\s+at)\b",
    re.IGNORECASE,
)

BUILD_HASH_RE = re.compile(
    r"\b(?:build|commit|version|sha|git|revision|hash)\s*[:#=]?\s*[a-f0-9]{7,64}\b|\b[a-f0-9]{32,64}\b",
    re.IGNORECASE,
)

# Domain Category Patterns: (compiled_regex, label)
PRICING_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"[$€£¥₹]\s*\d+(?:\.\d{1,2})?(?:\s*/\s*(?:mo|month|yr|year|seat|user|license|agent|dev|hour|day))?", re.IGNORECASE), "currency_price"),
    (re.compile(r"\b\d+(?:\.\d{1,2})?\s*(?:usd|eur|gbp|cad|aud|inr|jpy)\b", re.IGNORECASE), "currency_code"),
    (re.compile(r"\b(?:free|starter|basic|pro|growth|business|enterprise|team|premium|scale|custom)\s+(?:tier|plan|pricing|edition|package)\b", re.IGNORECASE), "pricing_tier"),
    (re.compile(r"/(?:mo|month|yr|year|seat|user|license|agent|dev|hour|day)\b", re.IGNORECASE), "billing_period"),
    (re.compile(r"\b(?:per\s+(?:month|year|user|seat|license)|billed\s+(?:monthly|annually|yearly))\b", re.IGNORECASE), "billing_period"),
    (re.compile(r"\b(?:pricing|price\s+(?:increase|decrease|update|change|cut|drop)|discount|discounts|free\s+trial|money-back|annual(?:ly)?\s+billing)\b", re.IGNORECASE), "pricing_update"),
]

FEATURE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:introducing|announcing|now\s+available|just\s+shipped|we(?:'re|\s+are)\s+excited\s+to\s+announce|we\s+just\s+launched|proud\s+to\s+announce)\b", re.IGNORECASE), "launch_announcement"),
    (re.compile(r"\b(?:new\s+feature|new\s+features|major\s+update|minor\s+update|changelog|release\s+notes|what'?s\s+new|product\s+update)\b", re.IGNORECASE), "feature_release"),
    (re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\s+(?:release|is\s+out|launched|is\s+live|has\s+shipped)\b", re.IGNORECASE), "version_release"),
    (re.compile(r"\b(?:beta\s+release|general\s+availability|\bGA\b(?:\s+launch|\s+release|\s+is\s+live)?|public\s+beta|private\s+beta|early\s+access|preview\s+release)\b", re.IGNORECASE), "release_status"),
]

POSITIONING_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:our\s+mission|value\s+proposition|tagline|mission\s+statement|brand\s+promise)\b", re.IGNORECASE), "mission"),
    (re.compile(r"\b(?:the\s+(?:only|leading|#1|fastest-growing|premier|modern|best-in-class))\b", re.IGNORECASE), "superlative"),
    (re.compile(r"\b(?:built\s+for\s+(?:enterprise|startups|teams|developers|businesses|modern\s+teams)|enterprise-grade|all-in-one\s+platform)\b", re.IGNORECASE), "target_audience"),
    (re.compile(r"\b(?:reimagining\s+how|empowering\s+teams\s+to|trusted\s+by\s+\d+[%+]?|the\s+future\s+of|next-generation|next\s+gen)\b", re.IGNORECASE), "narrative"),
]

DOCUMENTATION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:api\s+reference|api\s+endpoint|sdk\s+docs|quickstart\s+guide|developer\s+docs|rest\s+api|api\s+documentation|getting\s+started\s+guide)\b", re.IGNORECASE), "api_reference"),
    (re.compile(r"\b(?:curl\s+-X|(?:GET|POST|PUT|DELETE|PATCH)\s+/[a-zA-Z0-9_/{}]+)\b", re.IGNORECASE), "endpoint_spec"),
    (re.compile(r"\b(?:request\s+payload|response\s+body|query\s+parameter|status\s+code\s+\d{3}|bearer\s+token|webhook\s+payload|openapi|endpoint\s+url)\b", re.IGNORECASE), "technical_param"),
]

BLOG_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:\d+\s+min\s+read|by\s+[A-Z][a-z]+\s+[A-Z][a-z]+|published\s+on\s+[A-Z][a-z]+\s+\d{1,2}|written\s+by)\b", re.IGNORECASE), "byline"),
    (re.compile(r"\b(?:blog\s+post|latest\s+posts|read\s+the\s+full\s+article|table\s+of\s+contents|press\s+release|guest\s+post)\b", re.IGNORECASE), "article_reference"),
    (re.compile(r"\b(?:Title:\s*|Link:\s*https?://|Published:\s*|Summary:\s*)", re.IGNORECASE), "feed_entry"),
]


@dataclass(frozen=True)
class ClassificationResult:
    """Dataclass holding the classification output of a diff inspection."""

    is_meaningful: bool
    category: str
    significance_score: float
    summary: str
    reasons: List[str] = field(default_factory=list)
    detected_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert classification result to a JSON-serializable dictionary."""
        return {
            "is_meaningful": self.is_meaningful,
            "category": self.category,
            "significance_score": self.significance_score,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "detected_keywords": list(self.detected_keywords),
        }


def _extract_diff_lines(diff_unified: str) -> Tuple[List[str], List[str], int]:
    """
    Parse a unified diff string into added lines, removed lines, and hunk count.
    Excludes diff header lines ('---', '+++').
    """
    if not diff_unified:
        return [], [], 0

    diff_lines = diff_unified.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    added_lines: List[str] = []
    removed_lines: List[str] = []
    hunk_count = 0

    for line in diff_lines:
        if line.startswith("@@"):
            hunk_count += 1
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines.append(line[1:])

    return added_lines, removed_lines, hunk_count


def _deduplicate_keywords(keywords: List[str]) -> List[str]:
    """
    Deduplicate keywords preserving order, eliminating redundant substrings.
    """
    unique: List[str] = []
    for kw in keywords:
        clean = kw.strip()
        if not clean:
            continue
        # Avoid exact duplicate (case-insensitive)
        if any(clean.lower() == u.lower() for u in unique):
            continue
        # Avoid adding a shorter string if an existing keyword already encompasses it
        if any(clean.lower() in u.lower() for u in unique):
            continue
        unique.append(clean)
    return unique


def _find_matches_for_patterns(patterns: List[Tuple[re.Pattern, str]], text: str) -> List[str]:
    """Find all unique pattern matches in text."""
    matches: List[str] = []
    for pattern, _ in patterns:
        for m in pattern.finditer(text):
            val = m.group(0).strip()
            if val and val not in matches:
                matches.append(val)
    return _deduplicate_keywords(matches)


def _is_noise_line(line: str) -> bool:
    """Check if an individual delta line is cosmetic or token/cookie noise."""
    clean = line.strip()
    if not clean:
        return True
    if re.sub(r"[^\w\s]", "", clean) == "":
        return True
    return bool(
        COOKIE_GDPR_RE.search(clean)
        or TOKEN_CSRF_RE.search(clean)
        or SESSION_TRACE_RE.search(clean)
        or BUILD_HASH_RE.search(clean)
    )


class MeaningfulnessClassifier:
    """
    Deterministic rule-based and regex classifier for competitive snapshot diffs.
    Categorizes meaningful vs noise changes and calculates continuous significance scores.
    """

    @classmethod
    def classify(
        cls,
        diff_unified: str = "",
        diff_stats: Optional[Dict[str, Any]] = None,
        old_text: str = "",
        new_text: str = "",
    ) -> ClassificationResult:
        """
        Classify a unified diff and snapshot text.

        Parameters:
        - diff_unified: Line-by-line unified diff text.
        - diff_stats: Optional dictionary containing stats (lines_added, lines_removed, similarity_ratio, etc.).
        - old_text: Previous snapshot normalized content (optional).
        - new_text: Current snapshot normalized content (optional).

        Returns:
        - ClassificationResult with is_meaningful, category, significance_score, summary, reasons, detected_keywords.
        """
        diff_str = (diff_unified or "").strip()
        old_str = old_text or ""
        new_str = new_text or ""

        # Parse unified diff lines
        added_lines, removed_lines, hunk_count = _extract_diff_lines(diff_str)

        # Fallback: if diff_unified wasn't supplied but old_text and new_text are
        if not diff_str and (old_str or new_str):
            if old_str == new_str:
                return ClassificationResult(
                    is_meaningful=False,
                    category="noise",
                    significance_score=0.0,
                    summary="No changes detected.",
                    reasons=["No content differences between snapshots."],
                    detected_keywords=[],
                )
            generated_diff = list(
                difflib.unified_diff(
                    old_str.splitlines(),
                    new_str.splitlines(),
                    fromfile="a",
                    tofile="b",
                    lineterm="",
                )
            )
            diff_str = "\n".join(generated_diff)
            added_lines, removed_lines, hunk_count = _extract_diff_lines(diff_str)

        # Extract stats
        lines_added = len(added_lines)
        lines_removed = len(removed_lines)
        if diff_stats is not None:
            lines_added = int(diff_stats.get("lines_added", lines_added))
            lines_removed = int(diff_stats.get("lines_removed", lines_removed))
            hunk_count = int(diff_stats.get("hunk_count", hunk_count))
            similarity_ratio = float(diff_stats.get("similarity_ratio", 0.5))
        else:
            if old_str or new_str:
                similarity_ratio = round(
                    difflib.SequenceMatcher(None, old_str.splitlines(), new_str.splitlines()).ratio(),
                    4,
                )
            else:
                similarity_ratio = 0.5

        # Empty diff or zero changes
        if not diff_str and not added_lines and not removed_lines:
            return ClassificationResult(
                is_meaningful=False,
                category="noise",
                significance_score=0.0,
                summary="No changes detected.",
                reasons=["No changes detected in diff."],
                detected_keywords=[],
            )

        # Delta text for domain inspection
        delta_added = "\n".join(added_lines)
        delta_removed = "\n".join(removed_lines)
        delta_text = f"{delta_added}\n{delta_removed}".strip()

        # Step 1: Detect substantive signals in delta text
        pricing_matches = _find_matches_for_patterns(PRICING_PATTERNS, delta_text)
        feature_matches = _find_matches_for_patterns(FEATURE_PATTERNS, delta_text)
        positioning_matches = _find_matches_for_patterns(POSITIONING_PATTERNS, delta_text)
        doc_matches = _find_matches_for_patterns(DOCUMENTATION_PATTERNS, delta_text)
        blog_matches = _find_matches_for_patterns(BLOG_PATTERNS, delta_text)

        has_substantive_signals = bool(
            pricing_matches or feature_matches or positioning_matches or doc_matches or blog_matches
        )

        # Step 2: Noise Filtering Pipeline (only if no substantive signals override)
        if not has_substantive_signals:
            # 2.1 Pure whitespace changes
            is_pure_whitespace = False
            if old_str and new_str:
                if re.sub(r"\s+", " ", old_str).strip() == re.sub(r"\s+", " ", new_str).strip():
                    is_pure_whitespace = True
            if not is_pure_whitespace and added_lines and removed_lines:
                added_joined = "".join(re.sub(r"\s+", "", l) for l in added_lines)
                removed_joined = "".join(re.sub(r"\s+", "", l) for l in removed_lines)
                if added_joined == removed_joined:
                    is_pure_whitespace = True
            if not is_pure_whitespace and (added_lines or removed_lines):
                if all(not l.strip() for l in added_lines + removed_lines):
                    is_pure_whitespace = True

            if is_pure_whitespace:
                return ClassificationResult(
                    is_meaningful=False,
                    category="noise",
                    significance_score=0.0,
                    summary="Cosmetic whitespace formatting changes.",
                    reasons=["Whitespace formatting changes only."],
                    detected_keywords=[],
                )

            # 2.2 Punctuation and cosmetic character variations
            is_punctuation_only = False
            if old_str and new_str:
                old_clean_punct = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", old_str)).strip()
                new_clean_punct = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", new_str)).strip()
                if old_clean_punct == new_clean_punct or re.sub(r"\W+", "", old_str) == re.sub(r"\W+", "", new_str):
                    is_punctuation_only = True
            if not is_punctuation_only and added_lines and removed_lines:
                added_no_punct = "".join(re.sub(r"\W+", "", l) for l in added_lines)
                removed_no_punct = "".join(re.sub(r"\W+", "", l) for l in removed_lines)
                if added_no_punct == removed_no_punct:
                    is_punctuation_only = True

            if is_punctuation_only:
                return ClassificationResult(
                    is_meaningful=False,
                    category="noise",
                    significance_score=0.0,
                    summary="Punctuation and cosmetic character edits only.",
                    reasons=["Punctuation and cosmetic character variations only."],
                    detected_keywords=[],
                )

            # 2.3 Copyright year roll-forward
            is_copyright_rollforward = False
            if old_str and new_str:
                old_sub = COPYRIGHT_RE.sub("[COPYRIGHT_YEAR]", old_str).strip()
                new_sub = COPYRIGHT_RE.sub("[COPYRIGHT_YEAR]", new_str).strip()
                if old_sub == new_sub and COPYRIGHT_RE.search(old_str):
                    is_copyright_rollforward = True

            if not is_copyright_rollforward and added_lines and removed_lines:
                all_copyright = all(COPYRIGHT_RE.search(l) for l in added_lines + removed_lines if l.strip())
                if all_copyright:
                    added_sub = [COPYRIGHT_RE.sub("[COPYRIGHT_YEAR]", l).strip() for l in added_lines if l.strip()]
                    removed_sub = [COPYRIGHT_RE.sub("[COPYRIGHT_YEAR]", l).strip() for l in removed_lines if l.strip()]
                    if added_sub == removed_sub:
                        is_copyright_rollforward = True

            if is_copyright_rollforward:
                return ClassificationResult(
                    is_meaningful=False,
                    category="noise",
                    significance_score=0.0,
                    summary="Copyright year roll-forward.",
                    reasons=["Copyright year roll-forward."],
                    detected_keywords=[],
                )

            # 2.4 Cookie banner, GDPR consent, CSRF tokens, session IDs, build/commit hashes
            all_delta_lines = [l for l in added_lines + removed_lines if l.strip()]
            if all_delta_lines and all(_is_noise_line(l) for l in all_delta_lines):
                # Identify specific noise reason
                has_cookie = any(COOKIE_GDPR_RE.search(l) for l in all_delta_lines)
                has_token = any(TOKEN_CSRF_RE.search(l) for l in all_delta_lines)
                has_session = any(SESSION_TRACE_RE.search(l) for l in all_delta_lines)
                has_build = any(BUILD_HASH_RE.search(l) for l in all_delta_lines)

                reasons: List[str] = []
                if has_cookie:
                    reasons.append("Cookie banner and GDPR consent variations.")
                if has_token:
                    reasons.append("CSRF or authentication token variations.")
                if has_session:
                    reasons.append("Session ID, request ID, or dynamic timestamp variations.")
                if has_build:
                    reasons.append("Build, commit, or asset hash identifier variations.")

                if not reasons:
                    reasons.append("Dynamic banner or token variations.")

                summary = reasons[0] if len(reasons) == 1 else "Dynamic cookie banner, CSRF token, or build identifier variations."
                return ClassificationResult(
                    is_meaningful=False,
                    category="noise",
                    significance_score=0.0,
                    summary=summary,
                    reasons=reasons,
                    detected_keywords=[],
                )

            # 2.5 Micro-delta below threshold with no keywords
            is_micro = False
            if old_str and new_str:
                char_sim = difflib.SequenceMatcher(None, old_str, new_str).ratio()
                char_diff = abs(len(new_str) - len(old_str))
                if char_diff <= 2 and char_sim >= 0.85:
                    is_micro = True
            elif added_lines and removed_lines:
                added_joined = " ".join(added_lines)
                removed_joined = " ".join(removed_lines)
                char_sim = difflib.SequenceMatcher(None, removed_joined, added_joined).ratio()
                char_diff = abs(len(added_joined) - len(removed_joined))
                if char_diff <= 2 and char_sim >= 0.85:
                    is_micro = True

            if is_micro:
                return ClassificationResult(
                    is_meaningful=False,
                    category="noise",
                    significance_score=0.0,
                    summary="Cosmetic micro-change filtered.",
                    reasons=["Micro-delta below threshold with no domain keywords."],
                    detected_keywords=[],
                )

        # Step 3: Substantive Domain Categorization (in priority order)
        category: str
        detected_keywords: List[str]
        reasons = []

        if pricing_matches:
            category = "pricing_change"
            detected_keywords = pricing_matches
            reasons = ["Pricing tier, currency, or billing updates detected."]
        elif feature_matches:
            category = "feature_announcement"
            detected_keywords = feature_matches
            reasons = ["Feature announcement, launch, release notes, or version update detected."]
        elif positioning_matches:
            category = "positioning_shift"
            detected_keywords = positioning_matches
            reasons = ["Positioning, mission statement, or target audience shift detected."]
        elif doc_matches:
            category = "documentation_update"
            detected_keywords = doc_matches
            reasons = ["API reference, endpoint, SDK documentation, or technical spec updates detected."]
        elif blog_matches:
            category = "blog_post"
            detected_keywords = blog_matches
            reasons = ["Blog post, publication byline, or article feed updates detected."]
        else:
            category = "unknown"
            detected_keywords = []
            reasons = ["Content modified without matching specific domain categories."]

        # Step 4: Continuous Significance Score Calculation
        base_score = BASE_SCORES[category]

        # Volume modifier
        lines_changed = lines_added + lines_removed
        vol_mod = 0.0
        if lines_changed > 25:
            vol_mod = 0.05
        elif lines_changed < 3:
            vol_mod = -0.05

        # Similarity modifier
        sim_mod = 0.0
        if similarity_ratio < 0.30:
            sim_mod = 0.05
        elif similarity_ratio > 0.90:
            sim_mod = -0.05

        # Density modifier
        dense_mod = 0.0
        if detected_keywords:
            additional_matches = max(0, min(3, len(detected_keywords) - 1))
            dense_mod = round(additional_matches * 0.03, 4)

        raw_score = base_score + vol_mod + sim_mod + dense_mod
        significance_score = round(max(0.20, min(1.00, raw_score)), 2)

        # Step 5: Informative Summary Generation
        if lines_added > 0 and lines_removed > 0:
            line_detail = f"(+{lines_added} {'line' if lines_added == 1 else 'lines'}, -{lines_removed} {'line' if lines_removed == 1 else 'lines'})"
        elif lines_added > 0:
            line_detail = f"(+{lines_added} {'line' if lines_added == 1 else 'lines'})"
        elif lines_removed > 0:
            line_detail = f"(-{lines_removed} {'line' if lines_removed == 1 else 'lines'})"
        else:
            line_detail = ""

        if category == "pricing_change":
            kw_str = ", ".join(detected_keywords[:3])
            summary = f"Pricing change detected: mentions {kw_str} {line_detail}".strip()
        elif category == "feature_announcement":
            kw_str = ", ".join(detected_keywords[:3])
            summary = f"Feature announcement detected: mentions {kw_str} {line_detail}".strip()
        elif category == "positioning_shift":
            kw_str = ", ".join(detected_keywords[:3])
            summary = f"Positioning shift detected: mentions {kw_str} {line_detail}".strip()
        elif category == "documentation_update":
            kw_str = ", ".join(detected_keywords[:3])
            summary = f"Documentation update detected: mentions {kw_str} {line_detail}".strip()
        elif category == "blog_post":
            kw_str = ", ".join(detected_keywords[:3])
            summary = f"Blog post detected: mentions {kw_str} {line_detail}".strip()
        else:
            # category == "unknown"
            if lines_added > 0 or lines_removed > 0:
                if hunk_count > 0:
                    summary = f"Content modified: {lines_added} {'line' if lines_added == 1 else 'lines'} added, {lines_removed} {'line' if lines_removed == 1 else 'lines'} removed across {hunk_count} {'hunk' if hunk_count == 1 else 'hunks'}."
                else:
                    summary = f"Content modified: {lines_added} {'line' if lines_added == 1 else 'lines'} added, {lines_removed} {'line' if lines_removed == 1 else 'lines'} removed."
            else:
                summary = "Content modified."

        return ClassificationResult(
            is_meaningful=True,
            category=category,
            significance_score=significance_score,
            summary=summary,
            reasons=reasons,
            detected_keywords=detected_keywords,
        )
