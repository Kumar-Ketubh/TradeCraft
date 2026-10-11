"""
Unit tests for MeaningfulnessClassifier and ClassificationResult.

Validates:
- Noise suppression rules (whitespace, punctuation, copyright roll-forward, cookie banners, CSRF/tokens, session IDs, commit hashes).
- Substantive domain categorization (pricing_change, feature_announcement, positioning_shift, documentation_update, blog_post, unknown).
- Continuous significance scoring (0.0 for noise, >= 0.70 for pricing/features, clamped to [0.0, 1.0]).
- Summary string formatting and keyword extraction.
- Interface contracts and edge case resilience.
"""

import pytest

try:
    from app.classifiers import ClassificationResult, MeaningfulnessClassifier
except ImportError:
    from backend.app.classifiers import ClassificationResult, MeaningfulnessClassifier


# ============================================================================
# 1. Noise Filtering Tests
# ============================================================================

def test_noise_pure_whitespace_indentation():
    """Whitespace indentation change is classified as noise with 0.0 score."""
    diff = """--- a
+++ b
@@ -1,3 +1,3 @@
 def process():
-    return True
+  return True
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="def process():\n    return True",
        new_text="def process():\n  return True",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0
    assert "whitespace" in result.summary.lower()


def test_noise_pure_whitespace_blank_lines():
    """Adding or removing empty lines is classified as noise."""
    diff = """--- a
+++ b
@@ -1,2 +1,4 @@
 Welcome to TradeCraft
+
+
 Monitored content
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_pure_whitespace_trailing_spaces():
    """Trailing whitespace additions are classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-Analytics Dashboard
+Analytics Dashboard   
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="Analytics Dashboard",
        new_text="Analytics Dashboard   ",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_punctuation_only_period_to_exclamation():
    """Punctuation variation from period to exclamation mark is classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-Welcome to our platform.
+Welcome to our platform!
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="Welcome to our platform.",
        new_text="Welcome to our platform!",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0
    assert "punctuation" in result.summary.lower()


def test_noise_punctuation_only_dashes_and_colons():
    """Changing colon to dash or em-dash is classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-TradeCraft: Competitive Intelligence
+TradeCraft - Competitive Intelligence
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="TradeCraft: Competitive Intelligence",
        new_text="TradeCraft - Competitive Intelligence",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_copyright_roll_forward_single_year():
    """Updating copyright year from 2024 to 2025 is classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-© 2024 TradeCraft Inc. All rights reserved.
+© 2025 TradeCraft Inc. All rights reserved.
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="© 2024 TradeCraft Inc. All rights reserved.",
        new_text="© 2025 TradeCraft Inc. All rights reserved.",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0
    assert "copyright" in result.summary.lower()


def test_noise_copyright_roll_forward_year_range():
    """Updating copyright range e.g. 2020-2024 to 2020-2025 is classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-Copyright 2020-2024 Acme Corporation
+Copyright 2020-2025 Acme Corporation
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="Copyright 2020-2024 Acme Corporation",
        new_text="Copyright 2020-2025 Acme Corporation",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_copyright_roll_forward_html_entity():
    """HTML entity &copy; year update is classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-&copy; 2024 CloudServices LLC
+&copy; 2025 CloudServices LLC
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="&copy; 2024 CloudServices LLC",
        new_text="&copy; 2025 CloudServices LLC",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_cookie_banner_acceptance():
    """Dynamic cookie banner variations are classified as noise."""
    diff = """--- a
+++ b
@@ -1,2 +1,2 @@
-We use cookies to improve your browsing experience. Accept all cookies.
+We use cookies to ensure optimal performance. Manage cookie preferences.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0
    assert any("cookie" in r.lower() for r in result.reasons)


def test_noise_gdpr_consent_preferences():
    """GDPR tracking and consent changes are classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
+This site complies with GDPR tracking consent regulations. Manage privacy settings.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_csrf_token_change():
    """Dynamic CSRF / authenticity token mutations are classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-<input type="hidden" name="csrf_token" value="8f9a0b1c2d3e4f5a6b7c" />
+<input type="hidden" name="csrf_token" value="9a0b1c2d3e4f5a6b7c8d" />
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0
    assert any("csrf" in r.lower() or "token" in r.lower() for r in result.reasons)


def test_noise_session_id_and_trace_id():
    """Session IDs, trace IDs, and request IDs are classified as noise."""
    diff = """--- a
+++ b
@@ -1,2 +1,2 @@
-session_id = "sess_1029384756"
+session_id = "sess_5647382910"
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_build_and_git_commit_hashes():
    """Dynamic build numbers and git commit hashes are classified as noise."""
    diff = """--- a
+++ b
@@ -1,2 +1,2 @@
-<!-- Build: 7a8b9c0d1e2f -->
+<!-- Build: 9f8e7d6c5b4a -->
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


def test_noise_empty_diff_and_identical_texts():
    """Empty diff or identical snapshot texts return noise with zero score."""
    result = MeaningfulnessClassifier.classify(
        diff_unified="",
        old_text="Identical content",
        new_text="Identical content",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0
    assert "no changes detected" in result.summary.lower()


def test_noise_micro_delta_below_threshold():
    """Cosmetic 1-character typo edit without keywords is classified as noise."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-color
+colour
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="color",
        new_text="colour",
    )
    assert result.is_meaningful is False
    assert result.category == "noise"
    assert result.significance_score == 0.0


# ============================================================================
# 2. Substantive Category Tests
# ============================================================================

def test_category_pricing_change_currency_and_tier():
    """Detects pricing change with tier names and currency values."""
    diff = """--- a
+++ b
@@ -1,2 +1,3 @@
-Starter Plan: $29/mo
+Pro Tier: $49/mo
+Enterprise Tier: custom pricing
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 2, "lines_removed": 1, "similarity_ratio": 0.5},
    )
    assert result.is_meaningful is True
    assert result.category == "pricing_change"
    assert result.significance_score >= 0.70
    assert "$49/mo" in result.detected_keywords or "$49" in result.detected_keywords
    assert any("pro" in kw.lower() for kw in result.detected_keywords)
    assert "pricing change detected" in result.summary.lower()


def test_category_pricing_change_billing_frequency():
    """Detects billing periods like annual billing and per user per month."""
    diff = """--- a
+++ b
@@ -1 +1,2 @@
+Billed annually: save 20%
+All plans charged per user per month
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "pricing_change"
    assert result.significance_score >= 0.70


def test_category_pricing_change_international_currencies():
    """Detects EUR, GBP, and JPY currencies in pricing changes."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-Basic plan: €19/mo
+Basic plan: £25/mo
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "pricing_change"
    assert result.significance_score >= 0.70


def test_category_feature_announcement_launch_words():
    """Detects feature announcements using launch words like 'introducing'."""
    diff = """--- a
+++ b
@@ -1 +1,3 @@
+Introducing Real-Time Collaborative Canvas!
+We are excited to announce our major update shipped today.
+Now available to all teams.
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 3, "lines_removed": 0, "similarity_ratio": 0.0},
    )
    assert result.is_meaningful is True
    assert result.category == "feature_announcement"
    assert result.significance_score >= 0.70
    assert any("introducing" in kw.lower() for kw in result.detected_keywords)
    assert "feature announcement detected" in result.summary.lower()


def test_category_feature_announcement_version_release():
    """Detects versioned releases and changelogs."""
    diff = """--- a
+++ b
@@ -1 +1,2 @@
+v2.4.0 release is out!
+Check out the changelog and release notes for what's new.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "feature_announcement"
    assert result.significance_score >= 0.70


def test_category_feature_announcement_beta_and_ga():
    """Detects General Availability (GA) and Beta announcements."""
    diff = """--- a
+++ b
@@ -1 +1 @@
+Enterprise Single Sign-On has reached General Availability GA launch!
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "feature_announcement"
    assert result.significance_score >= 0.70


def test_category_positioning_shift_mission_and_value_prop():
    """Detects strategic positioning shifts and mission statements."""
    diff = """--- a
+++ b
@@ -1,2 +1,3 @@
-Simple project tracking software.
+Our mission is empowering modern engineering organizations.
+The #1 all-in-one platform for high-velocity teams.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "positioning_shift"
    assert 0.65 <= result.significance_score <= 1.0
    assert any("mission" in kw.lower() for kw in result.detected_keywords)
    assert "positioning shift detected" in result.summary.lower()


def test_category_positioning_shift_target_audience():
    """Detects shifting audience from startups to enterprise."""
    diff = """--- a
+++ b
@@ -1 +1,2 @@
+Built for enterprise-grade security and compliance.
+Reimagining how global enterprises operate.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "positioning_shift"
    assert 0.65 <= result.significance_score <= 1.0


def test_category_documentation_update_api_endpoints():
    """Detects API endpoint and REST documentation updates."""
    diff = """--- a
+++ b
@@ -1,3 +1,6 @@
+### API Reference
+Endpoint: POST /v1/workspaces/scan
+Request payload requires bearer token authentication.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "documentation_update"
    assert 0.55 <= result.significance_score <= 1.0
    assert any("api" in kw.lower() or "post" in kw.lower() for kw in result.detected_keywords)
    assert "documentation update detected" in result.summary.lower()


def test_category_documentation_update_curl_commands():
    """Detects curl commands and technical parameters in docs."""
    diff = """--- a
+++ b
@@ -1 +1,2 @@
+curl -X GET /v2/analytics/reports?status=200
+Response body contains query parameter details.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "documentation_update"
    assert 0.55 <= result.significance_score <= 1.0


def test_category_blog_post_byline_and_reading_time():
    """Detects blog post publishing with author byline and read time."""
    diff = """--- a
+++ b
@@ -1 +1,3 @@
+Published on October 11, 2026 by Jane Doe
+8 min read - read the full article below
+Latest posts in our engineering blog.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "blog_post"
    assert 0.50 <= result.significance_score <= 1.0
    assert "blog post detected" in result.summary.lower()


def test_category_blog_post_rss_entry_format():
    """Detects RSS normalized entry structure."""
    diff = """--- a
+++ b
@@ -1,4 +1,4 @@
+Title: Next-Gen Vector Search
+Link: https://example.com/blog/vector-search
+Published: Sun, 11 Oct 2026 12:00:00 GMT
+Summary: An in-depth exploration of vector indexes.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "blog_post"
    assert 0.50 <= result.significance_score <= 1.0


def test_category_unknown_substantive_content():
    """Substantive content changes not matching specific categories are classified as unknown."""
    diff = """--- a
+++ b
@@ -1,2 +1,3 @@
-Our office is located at 123 Main Street.
+Our new headquarters is located at 500 Market Plaza, Floor 14.
+Visitor parking is available on level P2.
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 2, "lines_removed": 1, "similarity_ratio": 0.4},
    )
    assert result.is_meaningful is True
    assert result.category == "unknown"
    assert 0.20 <= result.significance_score <= 0.60
    assert "content modified" in result.summary.lower()


# ============================================================================
# 3. Priority and Overlap Tests
# ============================================================================

def test_priority_pricing_over_feature_announcement():
    """When a feature announcement contains pricing changes, pricing takes priority."""
    diff = """--- a
+++ b
@@ -1 +1,3 @@
+Announcing our new feature: AI Copilot is now available!
+Add AI Copilot to your Pro Tier for only $19/mo per user.
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "pricing_change"
    assert result.significance_score >= 0.70


def test_substantive_overrides_noise_csrf_plus_pricing():
    """Diff containing both a CSRF token change and a pricing update is not treated as noise."""
    diff = """--- a
+++ b
@@ -1,2 +1,3 @@
 <input name="csrf_token" value="abc1234" />
+<input name="csrf_token" value="xyz9876" />
+Pro tier pricing updated to $59/mo
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "pricing_change"


def test_substantive_overrides_noise_cookie_plus_feature():
    """Diff containing both a cookie banner change and a new feature announcement is not noise."""
    diff = """--- a
+++ b
@@ -1,2 +1,3 @@
 We use cookies to enhance your experience.
+We use cookies and GDPR tracking consent.
+Introducing our major update v3.0!
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    assert result.is_meaningful is True
    assert result.category == "feature_announcement"


def test_copyright_plus_substantive_not_filtered_as_noise():
    """Diff updating copyright year while also adding real features is not filtered as noise."""
    diff = """--- a
+++ b
@@ -1,2 +1,3 @@
-© 2024 TradeCraft Inc.
+© 2025 TradeCraft Inc.
+Check out our new API reference documentation and endpoints.
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        old_text="© 2024 TradeCraft Inc.",
        new_text="© 2025 TradeCraft Inc.\nCheck out our new API reference documentation and endpoints.",
    )
    assert result.is_meaningful is True
    assert result.category == "documentation_update"


# ============================================================================
# 4. Significance Score Boundary Tests
# ============================================================================

def test_score_noise_is_zero():
    """All noise classifications yield a significance score of exactly 0.0."""
    res_ws = MeaningfulnessClassifier.classify(old_text="a", new_text="a  ")
    assert res_ws.significance_score == 0.0

    res_cr = MeaningfulnessClassifier.classify(old_text="© 2024 Acme", new_text="© 2025 Acme")
    assert res_cr.significance_score == 0.0


def test_score_pricing_exceeds_threshold():
    """Pricing changes consistently score >= 0.70 across all modifiers."""
    # Tiny 1-line change with high similarity (worst-case score deductions)
    diff = """--- a
+++ b
@@ -1 +1 @@
-Basic: $10/mo
+Basic: $12/mo
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 1, "lines_removed": 1, "similarity_ratio": 0.95},
    )
    assert result.category == "pricing_change"
    assert result.significance_score >= 0.70


def test_score_features_exceeds_threshold():
    """Feature announcements consistently score >= 0.70 across all modifiers."""
    diff = """--- a
+++ b
@@ -1 +1 @@
-Old version
+New version 2.0 release is out
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 1, "lines_removed": 1, "similarity_ratio": 0.95},
    )
    assert result.category == "feature_announcement"
    assert result.significance_score >= 0.70


def test_score_volume_modifier_boost_for_large_diff():
    """Large diffs with > 25 lines receive a volume modifier boost."""
    lines_added = ["+Item " + str(i) for i in range(30)]
    diff = "--- a\n+++ b\n@@ -0,0 +1,30 @@\n" + "\n".join(lines_added) + "\n+Built for enterprise teams"
    res_large = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 31, "lines_removed": 0, "similarity_ratio": 0.1},
    )
    assert res_large.significance_score >= 0.80


def test_score_always_clamped_between_zero_and_one():
    """Scores for any classification are strictly clamped between 0.0 and 1.0."""
    # Test maximum possible score
    diff_huge = "--- a\n+++ b\n@@ -0,0 +1,50 @@\n" + "\n".join(["+Pro tier $99/mo annual discount price " + str(i) for i in range(50)])
    res_max = MeaningfulnessClassifier.classify(
        diff_unified=diff_huge,
        diff_stats={"lines_added": 50, "lines_removed": 0, "similarity_ratio": 0.0},
    )
    assert 0.0 <= res_max.significance_score <= 1.0

    # Test unknown minimal score
    diff_tiny = "--- a\n+++ b\n@@ -1 +1 @@\n-Note A\n+Note B\n"
    res_min = MeaningfulnessClassifier.classify(
        diff_unified=diff_tiny,
        diff_stats={"lines_added": 1, "lines_removed": 1, "similarity_ratio": 0.95},
    )
    assert 0.20 <= res_min.significance_score <= 1.0


# ============================================================================
# 5. Summary Formatting and Keyword Tests
# ============================================================================

def test_summary_pricing_contains_keyword_and_line_deltas():
    """Pricing summary formats keywords and line delta counts cleanly."""
    diff = """--- a
+++ b
@@ -1 +1,2 @@
-Starter Tier: $29/mo
+Pro Tier: $49/mo
+Save 20% on annual billing
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 2, "lines_removed": 1, "similarity_ratio": 0.5},
    )
    assert "Pricing change detected: mentions" in result.summary
    assert "(+2 lines, -1 line)" in result.summary


def test_summary_pluralization_single_line_vs_multi_lines():
    """Correct singular/plural line formatting (+1 line vs +2 lines)."""
    diff_single = "--- a\n+++ b\n@@ -0,0 +1 @@\n+Introducing our new product"
    res_single = MeaningfulnessClassifier.classify(diff_unified=diff_single)
    assert "(+1 line)" in res_single.summary

    diff_multi = "--- a\n+++ b\n@@ -0,0 +1,3 @@\n+Introducing A\n+Introducing B\n+Introducing C"
    res_multi = MeaningfulnessClassifier.classify(diff_unified=diff_multi)
    assert "(+3 lines)" in res_multi.summary


def test_summary_unknown_hunk_formatting():
    """Unknown category summarizes line changes and hunk count."""
    diff = """--- a
+++ b
@@ -1,2 +1,2 @@
-Line 1
+Line A
@@ -10,2 +10,2 @@
-Line 10
+Line X
"""
    result = MeaningfulnessClassifier.classify(
        diff_unified=diff,
        diff_stats={"lines_added": 2, "lines_removed": 2, "hunk_count": 2, "similarity_ratio": 0.5},
    )
    assert result.category == "unknown"
    assert "2 lines added, 2 lines removed across 2 hunks" in result.summary


def test_detected_keywords_deduplication():
    """Keywords are deduplicated without repetitive substrings."""
    diff = """--- a
+++ b
@@ -1 +1,2 @@
+Pro Tier is now $49/mo
+Annual discount on Pro Tier
"""
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    keywords_lower = [kw.lower() for kw in result.detected_keywords]
    # "pro tier" should appear only once in detected_keywords
    assert keywords_lower.count("pro tier") == 1


# ============================================================================
# 6. Classifier Interface and Contract Tests
# ============================================================================

def test_class_method_and_instance_method_parity():
    """MeaningfulnessClassifier works both statically and as an instantiated object."""
    diff = "--- a\n+++ b\n@@ -0,0 +1 @@\n+Pro Tier: $49/mo"
    res_static = MeaningfulnessClassifier.classify(diff_unified=diff)
    classifier_instance = MeaningfulnessClassifier()
    res_instance = classifier_instance.classify(diff_unified=diff)

    assert res_static.category == res_instance.category
    assert res_static.significance_score == res_instance.significance_score
    assert res_static.summary == res_instance.summary
    assert res_static.detected_keywords == res_instance.detected_keywords


def test_classify_with_diff_stats_none():
    """Classify tolerates diff_stats being None."""
    diff = "--- a\n+++ b\n@@ -1 +1 @@\n-Old text\n+New text"
    result = MeaningfulnessClassifier.classify(diff_unified=diff, diff_stats=None)
    assert result.is_meaningful is True
    assert result.category == "unknown"


def test_classify_without_diff_unified_using_old_and_new_text():
    """Classify computes diff on the fly when diff_unified is omitted."""
    result = MeaningfulnessClassifier.classify(
        diff_unified="",
        old_text="Old basic text",
        new_text="Pro Tier: $49/mo is now live",
    )
    assert result.is_meaningful is True
    assert result.category == "pricing_change"


def test_classification_result_to_dict():
    """ClassificationResult.to_dict converts dataclass to JSON-serializable dict."""
    diff = "--- a\n+++ b\n@@ -0,0 +1 @@\n+Pro Tier: $49/mo"
    result = MeaningfulnessClassifier.classify(diff_unified=diff)
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert result_dict["is_meaningful"] is True
    assert result_dict["category"] == "pricing_change"
    assert "significance_score" in result_dict
    assert "summary" in result_dict
    assert isinstance(result_dict["reasons"], list)
    assert isinstance(result_dict["detected_keywords"], list)


def test_classification_result_immutable_frozen():
    """ClassificationResult is a frozen immutable dataclass."""
    result = ClassificationResult(
        is_meaningful=True,
        category="pricing_change",
        significance_score=0.9,
        summary="Test summary",
    )
    with pytest.raises(Exception):
        result.is_meaningful = False  # type: ignore
