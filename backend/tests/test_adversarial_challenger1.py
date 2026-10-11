# backend/tests/test_adversarial_challenger1.py
"""
Adversarial Stress Test Suite for Phase 3 Data Collection & Snapshot Storage Engine
Authored by Challenger 1 (Adversarial Critic & Empirical Specialist)

Coverage:
1. Adversarial HTML Normalization (deeply nested, malformed, entities, obfuscated tags, SHA-256 invariance)
2. Adversarial RSS/Atom Parsing (mixed namespaces, missing roots, CDATA payloads, invalid timestamps, fallbacks)
3. Scan Service Concurrency & Fault Tolerance Stress (high concurrency, mixed failures, parallel execution, exception shielding)
4. Cascading Deletions Lifecycle & Referential Integrity (ORM cascade, raw SQL FK cascade, selective competitor/source deletion)
"""

import asyncio
import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import List
from unittest.mock import patch, MagicMock

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.adapters.base import AdapterResult, DEFAULT_TIMEOUT_SECONDS
from app.adapters.hashing import compute_content_hash
from app.adapters.html_adapter import HtmlAdapter, _BoilerplateStripper
from app.adapters.rss_adapter import RssAdapter
from app.models.competitor import Competitor
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.models.source import Source
from app.models.user import User
from app.models.workspace import Workspace
from app.services.scan_service import ScanService


# ============================================================================
# SECTION 1: ADVERSARIAL HTML NORMALIZATION
# ============================================================================

class TestAdversarialHtmlNormalization:
    """Adversarial stress-testing of HTML normalization and deterministic hashing."""

    def test_adv_html_deeply_nested_tags(self):
        """Verify normalization survives deeply nested tags without RecursionError or data loss."""
        depth = 200
        nested_open = "".join([f"<div id='nest-{i}' class='wrapper-{i}'>" for i in range(depth)])
        nested_close = "".join(["</div>" for _ in range(depth)])
        html = f"""
        <!DOCTYPE html>
        <html>
        <body>
            {nested_open}
            <p>Core intelligence: Competitor product launched at $99/mo.</p>
            {nested_close}
        </body>
        </html>
        """
        adapter = HtmlAdapter("https://example.com")
        normalized = adapter.normalize(html)
        assert "Core intelligence: Competitor product launched at $99/mo." in normalized
        assert normalized == "Core intelligence: Competitor product launched at $99/mo."
        expected_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        assert compute_content_hash(normalized) == expected_hash

    def test_adv_html_malformed_unclosed_tags(self):
        """Verify parser resilience against severely malformed, mismatched, and unclosed HTML tags."""
        malformed_html = """
        <html>
        <head><title>Unclosed Page
        <body>
        <div class="header">
            <h1>Product Overview
            <p>First paragraph without close tag
        <div class="content">
            <span class="highlight">Key feature: Real-time analytics
            <div>Nested div never closed
            <p>Second paragraph</b></i>
        <section>
            Unclosed section text here
        <!-- Unclosed HTML comment at the end
        """
        adapter = HtmlAdapter("https://example.com")
        normalized = adapter.normalize(malformed_html)
        assert "Product Overview" in normalized
        assert "First paragraph without close tag" in normalized
        assert "Key feature: Real-time analytics" in normalized
        assert "Nested div never closed" in normalized
        assert "Second paragraph" in normalized
        assert "Unclosed section text here" in normalized

    def test_adv_html_entity_encoding_permutations(self):
        """Verify HTML entity decoding produces consistent text across named, numeric, and hex entities."""
        # Core sentence: AT&T & Verizon "unlimited" plan: 100% > $50/mo 'special'
        raw_variants = [
            # Named entities
            "<p>AT&amp;T &amp; Verizon &quot;unlimited&quot; plan: 100% &gt; $50/mo &apos;special&apos;</p>",
            # Decimal numeric entities
            "<p>AT&#38;T &#38; Verizon &#34;unlimited&#34; plan: 100% &#62; $50/mo &#39;special&#39;</p>",
            # Hexadecimal numeric entities
            "<p>AT&#x26;T &#x26; Verizon &#x22;unlimited&#x22; plan: 100% &#x3e; $50/mo &#x27;special&#x27;</p>",
            # Mixed entities with non-breaking spaces
            "<p>AT&amp;T&nbsp;&amp;&nbsp;Verizon&nbsp;&quot;unlimited&quot;&#x20;plan:&#32;100%&#x20;&gt;&#x20;$50/mo&nbsp;&apos;special&apos;</p>",
        ]
        adapter = HtmlAdapter("https://example.com")
        normalized_results = [adapter.normalize(var) for var in raw_variants]
        first_norm = normalized_results[0]
        assert "AT&T & Verizon \"unlimited\" plan: 100% > $50/mo 'special'" in first_norm
        for norm in normalized_results[1:]:
            assert norm == first_norm, f"Entity variant produced inconsistent normalized text: {norm!r} != {first_norm!r}"
            assert compute_content_hash(norm) == compute_content_hash(first_norm)

    def test_adv_html_obfuscated_scripts_styles_and_comments(self):
        """Verify boilerplate suppression strips case-insensitive, obfuscated, and SVG-nested scripts/styles."""
        html = """
        <html>
        <head>
            <SCRIPT TYPE="text/javascript">
                var token = "SECRET_12345";
                var code = "<p>This is deceptive script content</p>";
            </SCRIPT>
            <sTyLe media="screen">
                body { background: red; font-family: sans-serif; }
                .ad-banner { display: block; }
            </StYlE>
        </head>
        <body>
            <NAV class="primary-nav">
                <a href="/home">Home</a>
                <a href="/pricing">Pricing</a>
            </NAV>
            <div id="main-content">
                <h2>Real Competitive Content</h2>
                <svg width="100" height="100">
                    <circle cx="50" cy="50" r="40" />
                    <script>alert("svg script injection");</script>
                </svg>
                <p>Enterprise subscription is $499 per seat per year.</p>
                <div class="ad-container-leaderboard" id="banner-ad-top">
                    Sponsored Advertisement: Buy our partner services!
                </div>
                <div class="cookie-consent-modal" role="banner">
                    Please accept our cookies to continue.
                </div>
                <IFRAME src="https://ads.example.com/frame">Track</IFRAME>
                <form action="/newsletter" method="POST">
                    <input type="email" name="email" value="spam@example.com" />
                    <button type="submit">Subscribe</button>
                </form>
            </div>
            <FOOTER class="site-footer">
                <p>&copy; 2026 Competitor Corp. All rights reserved.</p>
            </FOOTER>
        </body>
        </html>
        """
        adapter = HtmlAdapter("https://example.com")
        normalized = adapter.normalize(html)

        # Assert clean content preserved
        assert "Real Competitive Content" in normalized
        assert "Enterprise subscription is $499 per seat per year." in normalized

        # Assert noise stripped completely
        assert "SECRET_12345" not in normalized
        assert "deceptive script content" not in normalized
        assert "sans-serif" not in normalized
        assert "Home" not in normalized
        assert "svg script injection" not in normalized
        assert "Sponsored Advertisement" not in normalized
        assert "accept our cookies" not in normalized
        assert "spam@example.com" not in normalized
        assert "Competitor Corp" not in normalized

    def test_adv_html_deterministic_hashing_stress_generator(self):
        """
        Stress test deterministic content hashing across 20 distinct permutations
        containing random dynamic banners, ad IDs, dynamic timestamps, and whitespace.
        All 20 permutations must evaluate to the EXACT SAME SHA-256 hash.
        """
        adapter = HtmlAdapter("https://example.com")
        hashes = []

        for seed in range(20):
            # Inject randomized dynamic noise that must be stripped
            timestamp_str = f"2026-10-{seed:02d}T{seed:02d}:34:56Z"
            session_id = f"sess_{uuid.uuid4().hex}"
            ad_id = f"ad-banner-{seed * 997}"
            whitespace_padding = "  \n\t " * ((seed % 4) + 1)

            html_permutation = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <script>window.__SESSION__ = "{session_id}";</script>
                <style>.cls-{seed} {{ margin: 0; }}</style>
            </head>
            <body>
                <header>Navigation and Site Header</header>
                <div id="{ad_id}" class="advertisement top-banner">
                    Ad Click #{seed}: Sale 50% Off! Updated at {timestamp_str}
                </div>
                <div class="cookie-banner-notice" id="cookie-consent-{seed}">
                    Cookie notice consent token {session_id}
                </div>
                <main id="content">
                    <h1>TradeCraft Market Analysis</h1>
                    {whitespace_padding}
                    <p>Quarterly recurring revenue expanded by 34%.</p>
                    <div class="newsletter-signup-modal">Sign up for emails!</div>
                    <p>Customer retention remains at 94.2% across North America.</p>
                </main>
                <aside class="ad-sidebar">Sidebar Advertisement</aside>
                <footer>Footer links &copy; 2026</footer>
            </body>
            </html>
            """
            normalized = adapter.normalize(html_permutation)
            h = compute_content_hash(normalized)
            hashes.append(h)

        # Assert all 20 permutations have the identical hash
        assert len(set(hashes)) == 1, f"Expected 1 unique hash across 20 permutations, got {len(set(hashes))}: {set(hashes)}"
        assert hashes[0] == compute_content_hash("TradeCraft Market Analysis\nQuarterly recurring revenue expanded by 34%.\nCustomer retention remains at 94.2% across North America.")

    def test_adv_html_unicode_and_special_characters(self):
        """Verify HTML normalization survives unicode, emojis, C1 control chars, and zero-width spaces."""
        html = """
        <html>
        <body>
            <article>
                <h1>Competitor Intelligence \U0001F680</h1>
                <p>Features include: AI\u200b-powered forecasting &amp; \u202eRTL\u202c override support.</p>
                <p>Currency prices: €100 / £85 / ¥15,000 per month.</p>
            </article>
        </body>
        </html>
        """
        adapter = HtmlAdapter("https://example.com")
        norm = adapter.normalize(html)
        assert "Competitor Intelligence \U0001F680" in norm
        assert "€100 / £85 / ¥15,000 per month." in norm
        h = compute_content_hash(norm)
        assert len(h) == 64

    def test_adv_html_fallback_boilerplate_stripper_parity(self):
        """Verify _BoilerplateStripper fallback parser handles tags, void elements, and noise elements."""
        stripper = _BoilerplateStripper()
        sample_html = """
        <html>
        <head>
            <script>console.log('strip me');</script>
            <style>body { color: black; }</style>
        </head>
        <body>
            <header>Header noise</header>
            <div class="ad-banner">Ad noise</div>
            <div id="main">
                <h1>Fallback Test Title</h1>
                <p>Paragraph 1 with <br> break line.</p>
                <div class="cookie-popup">Cookie noise</div>
                <p>Paragraph 2 core data.</p>
            </div>
            <footer>Footer noise</footer>
        </body>
        </html>
        """
        stripper.feed(sample_html)
        raw_text = "".join(stripper.text_parts)
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw_text.splitlines() if line.strip()]
        result = "\n".join(lines)

        assert "Fallback Test Title" in result
        assert "Paragraph 1 with" in result
        assert "Paragraph 2 core data." in result
        assert "strip me" not in result
        assert "Header noise" not in result
        assert "Ad noise" not in result
        assert "Cookie noise" not in result
        assert "Footer noise" not in result


# ============================================================================
# SECTION 2: ADVERSARIAL RSS / ATOM PARSING
# ============================================================================

class TestAdversarialRssParsing:
    """Adversarial stress-testing of RSS and Atom syndication feed parsing."""

    def test_adv_rss_mixed_namespaces(self):
        """Verify parsing feeds with mixed XML namespaces (RSS 2.0, Dublin Core, Content encoded)."""
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"
             xmlns:dc="http://purl.org/dc/elements/1.1/"
             xmlns:content="http://purl.org/rss/1.0/modules/content/"
             xmlns:atom="http://www.w3.org/2005/Atom">
            <channel>
                <title>Competitor Intelligence Feed</title>
                <link>https://competitor.com/blog</link>
                <description>Latest company news and product launches</description>
                <item>
                    <title>Major Strategic Acquisition</title>
                    <link>https://competitor.com/news/acquisition-2026</link>
                    <dc:date>2026-10-10T14:30:00Z</dc:date>
                    <dc:creator>Jane Doe</dc:creator>
                    <content:encoded><![CDATA[<p>Full breakdown of the <b>$50M</b> acquisition.</p>]]></content:encoded>
                    <description>Summary of strategic acquisition.</description>
                </item>
            </channel>
        </rss>
        """
        adapter = RssAdapter("https://competitor.com/feed.xml")
        normalized = adapter.normalize(feed_xml)

        assert "Title: Major Strategic Acquisition" in normalized
        assert "Link: https://competitor.com/news/acquisition-2026" in normalized
        assert "2026-10-10" in normalized
        assert "Summary:" in normalized
        assert "acquisition" in normalized.lower()

    def test_adv_rss_missing_channel_and_malformed_xml_roots(self):
        """Verify resilience against feeds missing channel tags, bare feeds, or broken tags."""
        # 1. RSS with missing channel
        broken_rss = """<?xml version="1.0"?>
        <rss version="2.0">
            <item>
                <title>Item Without Channel</title>
                <link>https://example.com/item1</link>
                <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
                <description>Description text</description>
            </item>
        </rss>
        """
        adapter = RssAdapter("https://example.com/rss")
        norm1 = adapter.normalize(broken_rss)
        assert "Item Without Channel" in norm1 or norm1 == ""

        # 2. Completely empty container
        empty_rss = "<rss version=\"2.0\"><channel></channel></rss>"
        assert adapter.normalize(empty_rss) == ""

        # 3. Non-XML garbage
        garbage = "NOT_XML_AT_ALL <<>> <<? ?> foo bar baz"
        assert adapter.normalize(garbage) == ""

        # 4. Binary junk
        binary_garbage = "\x00\x01\x02\x03\xff\xfe\x00<xml>"
        assert adapter.normalize(binary_garbage) == ""

    def test_adv_rss_malicious_cdata_payloads(self):
        """Verify CDATA payloads containing HTML tags, scripts, and entities are safely sanitized."""
        cdata_feed = """<?xml version="1.0" encoding="utf-8"?>
        <rss version="2.0">
            <channel>
                <title>Feed with CDATA</title>
                <link>https://example.com</link>
                <description>Test</description>
                <item>
                    <title><![CDATA[Special <Offer>: 20% & Off]]></title>
                    <link>https://example.com/promo</link>
                    <pubDate>Wed, 14 Oct 2026 12:00:00 GMT</pubDate>
                    <description><![CDATA[
                        <div class="cdata-body">
                            <p>Here is our <b>new pricing tier</b> for 2026.</p>
                            <script type="text/javascript">document.write("evil injection");</script>
                            <a href="https://example.com/buy">Sign up now!</a>
                        </div>
                    ]]></description>
                </item>
            </channel>
        </rss>
        """
        adapter = RssAdapter("https://example.com/feed")
        normalized = adapter.normalize(cdata_feed)

        assert "Title: Special <Offer>: 20% & Off" in normalized or "Special" in normalized
        assert "Link: https://example.com/promo" in normalized
        # Assert HTML tags stripped from summary
        assert "<p>" not in normalized
        assert "</div>" not in normalized
        assert "<script" not in normalized
        assert "Here is our new pricing tier for 2026." in normalized
        assert "Sign up now!" in normalized

    def test_adv_rss_invalid_and_exotic_timestamps(self):
        """Verify timestamps in any arbitrary, non-standard, or corrupted format do not crash parser."""
        exotic_dates = [
            "2026-10-11T12:00:00.000+05:30",
            "Sun, 11 Oct 2026 10:30:00 -0400",
            "Invalid Date String From Broken Server",
            "NaN-NaN-NaN",
            "9999-99-99T99:99:99Z",
            "",
        ]
        for idx, date_str in enumerate(exotic_dates):
            feed = f"""<?xml version="1.0"?>
            <rss version="2.0">
                <channel>
                    <title>Test Feed {idx}</title>
                    <link>https://example.com</link>
                    <item>
                        <title>Entry {idx}</title>
                        <link>https://example.com/{idx}</link>
                        <pubDate>{date_str}</pubDate>
                        <description>Summary {idx}</description>
                    </item>
                </channel>
            </rss>
            """
            adapter = RssAdapter(f"https://example.com/{idx}")
            norm = adapter.normalize(feed)
            assert f"Title: Entry {idx}" in norm
            assert f"Summary: Summary {idx}" in norm

    def test_adv_rss_fallback_element_tree_extractor(self):
        """Directly verify standard library ElementTree fallback extractor on RSS and Atom feeds."""
        adapter = RssAdapter("https://example.com/feed")

        # 1. RSS 2.0 with ElementTree
        rss2 = """<rss version="2.0">
            <channel>
                <item>
                    <title>ET Item</title>
                    <link>https://example.com/et</link>
                    <pubDate>2026-10-11</pubDate>
                    <description>ET Description</description>
                </item>
            </channel>
        </rss>"""
        entries = adapter._extract_entries_element_tree(rss2)
        assert len(entries) == 1
        assert entries[0]["title"] == "ET Item"
        assert entries[0]["link"] == "https://example.com/et"
        assert entries[0]["summary"] == "ET Description"

        # 2. Atom feed with ElementTree
        atom = """<feed xmlns="http://www.w3.org/2005/Atom">
            <title>Atom Feed</title>
            <entry>
                <title>Atom Entry</title>
                <link href="https://example.com/atom" />
                <updated>2026-10-11T12:00:00Z</updated>
                <summary>Atom Summary</summary>
            </entry>
        </feed>"""
        atom_entries = adapter._extract_entries_element_tree(atom)
        assert len(atom_entries) == 1
        assert atom_entries[0]["title"] == "Atom Entry"
        assert atom_entries[0]["link"] == "https://example.com/atom"
        assert atom_entries[0]["summary"] == "Atom Summary"

    def test_adv_rss_high_volume_stress(self):
        """Verify RSS parser handles large feeds with 200 items efficiently without memory exhaustion."""
        items = "".join([
            f"<item><title>Item {i}</title><link>https://ex.com/{i}</link><pubDate>2026-10-11</pubDate><description>Desc {i}</description></item>"
            for i in range(200)
        ])
        feed = f"<rss version='2.0'><channel><title>Massive Feed</title>{items}</channel></rss>"
        adapter = RssAdapter("https://example.com/feed")
        normalized = adapter.normalize(feed)
        assert "Title: Item 0" in normalized
        assert "Title: Item 199" in normalized
        h = compute_content_hash(normalized)
        assert len(h) == 64



# ============================================================================
# SECTION 3: SCAN SERVICE CONCURRENCY & RESILIENCE STRESS
# ============================================================================

class TestAdversarialScanConcurrencyAndResilience:
    """Adversarial stress-testing of ScanService under high concurrency and mixed failures."""

    @pytest.mark.anyio
    async def test_adv_scan_service_high_concurrency_mixed_outcomes(self, db_session: Session):
        """
        Stress test batch scan with 50 concurrent sources exhibiting 7 distinct outcome types:
        - 15x 200 OK HTML
        - 10x 200 OK RSS
        - 5x 403 Forbidden
        - 5x 404 Not Found
        - 5x 500 Internal Server Error
        - 5x Read Timeout
        - 5x Connect Error
        Assert exactly 50 Snapshots persisted, status='partial', and counters exactly match.
        """
        # Setup workspace, competitor, and 50 sources
        user = User(name="Stress User", email=f"stress_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="Stress Test Workspace", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp = Competitor(name="Stress Competitor", workspace_id=ws.id, monitoring_enabled=True)
        db_session.add(comp)
        db_session.commit()

        sources: List[Source] = []
        for i in range(50):
            stype = "rss" if (15 <= i < 25) else "website"
            src = Source(
                competitor_id=comp.id,
                name=f"Stress Source {i:02d}",
                url=f"https://source-{i}.example.com/data",
                source_type=stype,
                monitoring_enabled=True,
            )
            db_session.add(src)
            sources.append(src)
        db_session.commit()

        # Mock HTTP transport simulating all 7 outcomes deterministically based on source index
        def custom_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            match = re.search(r"source-(\d+)", url_str)
            idx = int(match.group(1)) if match else 0

            if idx < 15:
                # 0-14: 200 OK HTML
                return httpx.Response(200, text=f"<html><body><h1>Success {idx}</h1><p>Data {idx}</p></body></html>")
            elif idx < 25:
                # 15-24: 200 OK RSS
                feed_xml = f"""<rss version="2.0"><channel><item><title>Feed {idx}</title><link>https://ex.com/{idx}</link><description>Desc {idx}</description></item></channel></rss>"""
                return httpx.Response(200, text=feed_xml)
            elif idx < 30:
                # 25-29: 403 Forbidden
                return httpx.Response(403, text="Forbidden Access")
            elif idx < 35:
                # 30-34: 404 Not Found
                return httpx.Response(404, text="Not Found")
            elif idx < 40:
                # 35-39: 500 Server Error
                return httpx.Response(500, text="Internal Server Error")
            elif idx < 45:
                # 40-44: Read Timeout
                raise httpx.ReadTimeout("Socket read timed out")
            else:
                # 45-49: Connect Error
                raise httpx.ConnectError("Connection refused by peer")

        transport = httpx.MockTransport(custom_handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            service = ScanService(db=db_session, client=mock_client)
            scan_run = await service.scan_workspace(ws.id)

        # Assert ScanRun state
        assert scan_run.total_sources == 50
        assert scan_run.successful_sources == 25  # 15 HTML + 10 RSS
        assert scan_run.failed_sources == 25      # 5(403) + 5(404) + 5(500) + 5(timeout) + 5(connect)
        assert scan_run.status == "partial"
        assert "25 of 50 sources failed" in (scan_run.error_message or "")
        assert scan_run.completed_at is not None

        # Verify database snapshot records
        snapshots = db_session.query(Snapshot).filter(Snapshot.scan_run_id == scan_run.id).all()
        assert len(snapshots) == 50

        success_snaps = [s for s in snapshots if s.status == "success"]
        error_snaps = [s for s in snapshots if s.status == "error"]
        assert len(success_snaps) == 25
        assert len(error_snaps) == 25

        # Check success snapshot attributes
        for s in success_snaps:
            assert s.status_code == 200
            assert s.content_hash is not None and len(s.content_hash) == 64
            assert s.normalized_content is not None
            assert s.error_message is None

        # Check error snapshot attributes
        for s in error_snaps:
            assert s.content_hash is None
            assert s.error_message is not None

    @pytest.mark.anyio
    async def test_adv_scan_service_parallel_concurrent_scans(self, db_session: Session):
        """
        Verify that multiple concurrent scan runs triggered simultaneously across workspaces
        complete without SQLite lock contention or ID collision.
        """
        user = User(name="Parallel User", email=f"parallel_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        # Create 3 distinct workspaces with sources
        workspaces = []
        for w_idx in range(3):
            ws = Workspace(name=f"Parallel Workspace {w_idx}", user_id=user.id)
            db_session.add(ws)
            db_session.commit()

            comp = Competitor(name=f"Comp {w_idx}", workspace_id=ws.id, monitoring_enabled=True)
            db_session.add(comp)
            db_session.commit()

            for s_idx in range(4):
                src = Source(
                    competitor_id=comp.id,
                    name=f"Source {w_idx}_{s_idx}",
                    url=f"https://parallel-{w_idx}-{s_idx}.com",
                    source_type="website",
                    monitoring_enabled=True,
                )
                db_session.add(src)
            db_session.commit()
            workspaces.append(ws)

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html><body><p>Parallel Data OK</p></body></html>")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            service = ScanService(db=db_session, client=mock_client)
            # Run all 3 workspace scans concurrently
            results = await asyncio.gather(
                service.scan_workspace(workspaces[0].id),
                service.scan_workspace(workspaces[1].id),
                service.scan_workspace(workspaces[2].id),
            )

        assert len(results) == 3
        scan_ids = [r.id for r in results]
        assert len(set(scan_ids)) == 3, "Each concurrent scan must receive a unique UUID"

        for r in results:
            assert r.status == "completed"
            assert r.total_sources == 4
            assert r.successful_sources == 4
            assert r.failed_sources == 0

        # Verify all 12 snapshots persisted cleanly
        all_snapshots = db_session.query(Snapshot).filter(Snapshot.scan_run_id.in_(scan_ids)).all()
        assert len(all_snapshots) == 12

    @pytest.mark.anyio
    async def test_adv_scan_service_adapter_exception_shielding(self, db_session: Session):
        """
        Verify that an unexpected unhandled exception inside an adapter does not abort
        the batch scan or crash the ScanService.
        """
        user = User(name="Shield User", email=f"shield_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="Shield WS", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp = Competitor(name="Shield Comp", workspace_id=ws.id, monitoring_enabled=True)
        db_session.add(comp)
        db_session.commit()

        s1 = Source(competitor_id=comp.id, name="Src Good", url="https://good.com", source_type="website")
        s2 = Source(competitor_id=comp.id, name="Src Exploding", url="https://explode.com", source_type="website")
        db_session.add_all([s1, s2])
        db_session.commit()

        async with httpx.AsyncClient() as client:
            service = ScanService(db=db_session, client=client)

            # Patch get_adapter_for_source so that s2 raises an explosive RuntimeError
            original_get_adapter = __import__("app.services.scan_service", fromlist=["get_adapter_for_source"]).get_adapter_for_source

            def exploding_get_adapter(source, client=None, timeout=DEFAULT_TIMEOUT_SECONDS):
                if source.name == "Src Exploding":
                    raise RuntimeError("Catastrophic adapter initialization explosion!")
                return original_get_adapter(source, client=client, timeout=timeout)

            with patch("app.services.scan_service.get_adapter_for_source", side_effect=exploding_get_adapter):
                with patch("app.adapters.html_adapter.HtmlAdapter.fetch", return_value=AdapterResult(
                    url="https://good.com", status="success", http_status=200,
                    raw_content="<html>OK</html>", normalized_content="OK", content_hash="hash123"
                )):
                    scan_run = await service.scan_workspace(ws.id)

        assert scan_run.total_sources == 2
        assert scan_run.successful_sources == 1
        assert scan_run.failed_sources == 1
        assert scan_run.status == "partial"

        # Check snapshots
        snapshots = db_session.query(Snapshot).filter(Snapshot.scan_run_id == scan_run.id).all()
        assert len(snapshots) == 2
        exploding_snap = next(s for s in snapshots if s.source_id == s2.id)
        assert exploding_snap.status == "error"
        assert "Catastrophic adapter initialization explosion!" in (exploding_snap.error_message or "")

    @pytest.mark.anyio
    async def test_adv_scan_service_all_failures_marks_failed_status(self, db_session: Session):
        """
        Verify that when 100% of sources fail to fetch, the ScanRun status transitions
        strictly to 'failed' rather than 'partial' or 'completed'.
        """
        user = User(name="Fail User", email=f"fail_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="All Fail WS", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp = Competitor(name="Fail Comp", workspace_id=ws.id, monitoring_enabled=True)
        db_session.add(comp)
        db_session.commit()

        for idx in range(3):
            src = Source(
                competitor_id=comp.id,
                name=f"Failing Src {idx}",
                url=f"https://fail-{idx}.com",
                source_type="website",
                monitoring_enabled=True,
            )
            db_session.add(src)
        db_session.commit()

        def fail_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(fail_handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            service = ScanService(db=db_session, client=mock_client)
            scan_run = await service.scan_workspace(ws.id)

        assert scan_run.total_sources == 3
        assert scan_run.successful_sources == 0
        assert scan_run.failed_sources == 3
        assert scan_run.status == "failed"
        assert "All 3 sources failed to fetch." in (scan_run.error_message or "")



# ============================================================================
# SECTION 4: CASCADING DELETIONS & REFERENTIAL INTEGRITY
# ============================================================================

class TestAdversarialCascadingDeletions:
    """Adversarial verification of cascading deletions across SQLite and PostgreSQL."""

    def test_adv_cascading_deletion_full_hierarchy_orm(self, db_session: Session):
        """
        Verify that deleting a Workspace via SQLAlchemy ORM cleans up:
        Workspace -> Competitors -> Sources -> ScanRuns -> Snapshots.
        Zero orphan rows must remain.
        """
        user = User(name="Cascade User", email=f"cascade_orm_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="WS to Delete", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp = Competitor(name="Comp to Delete", workspace_id=ws.id)
        db_session.add(comp)
        db_session.commit()

        src = Source(competitor_id=comp.id, name="Src to Delete", url="https://delete.com", source_type="website")
        db_session.add(src)
        db_session.commit()

        scan_run = ScanRun(
            workspace_id=ws.id,
            competitor_id=comp.id,
            status="completed",
            total_sources=1,
            successful_sources=1,
            failed_sources=0,
        )
        db_session.add(scan_run)
        db_session.commit()

        snap = Snapshot(
            scan_run_id=scan_run.id,
            source_id=src.id,
            status="success",
            status_code=200,
            raw_content="<html>test</html>",
            normalized_content="test",
            content_hash="hash",
        )
        db_session.add(snap)
        db_session.commit()

        ws_id = ws.id
        comp_id = comp.id
        src_id = src.id
        scan_id = scan_run.id
        snap_id = snap.id

        # Delete workspace via ORM
        db_session.delete(ws)
        db_session.commit()

        # Assert all child records deleted
        assert db_session.query(Workspace).filter(Workspace.id == ws_id).first() is None
        assert db_session.query(Competitor).filter(Competitor.id == comp_id).first() is None
        assert db_session.query(Source).filter(Source.id == src_id).first() is None
        assert db_session.query(ScanRun).filter(ScanRun.id == scan_id).first() is None
        assert db_session.query(Snapshot).filter(Snapshot.id == snap_id).first() is None

    def test_adv_cascading_deletion_direct_sql_foreign_keys(self, db_session: Session):
        """
        Verify that database-level FOREIGN KEY ON DELETE CASCADE constraints
        function when a workspace is deleted via direct raw SQL execution.
        """
        user = User(name="SQL Cascade User", email=f"cascade_sql_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="WS to SQL Delete", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp = Competitor(name="Comp to SQL Delete", workspace_id=ws.id)
        db_session.add(comp)
        db_session.commit()

        src = Source(competitor_id=comp.id, name="Src SQL", url="https://sql.com", source_type="website")
        db_session.add(src)
        db_session.commit()

        scan = ScanRun(workspace_id=ws.id, competitor_id=comp.id, status="completed", total_sources=1)
        db_session.add(scan)
        db_session.commit()

        snap = Snapshot(scan_run_id=scan.id, source_id=src.id, status="success")
        db_session.add(snap)
        db_session.commit()

        ws_id = ws.id
        scan_id = scan.id

        # Raw SQL delete bypassing SQLAlchemy ORM cascading hooks
        db_session.execute(text("DELETE FROM workspaces WHERE id = :wid"), {"wid": ws_id})
        db_session.commit()

        # Verify DB foreign keys cascaded cleanly
        remaining_comps = db_session.execute(text("SELECT count(*) FROM competitors WHERE workspace_id = :wid"), {"wid": ws_id}).scalar()
        remaining_scans = db_session.execute(text("SELECT count(*) FROM scan_runs WHERE workspace_id = :wid"), {"wid": ws_id}).scalar()
        remaining_snaps = db_session.execute(text("SELECT count(*) FROM snapshots WHERE scan_run_id = :sid"), {"sid": scan_id}).scalar()

        assert remaining_comps == 0, "Competitors must be cascade-deleted by foreign key constraint"
        assert remaining_scans == 0, "ScanRuns must be cascade-deleted by foreign key constraint"
        assert remaining_snaps == 0, "Snapshots must be cascade-deleted by foreign key constraint"

    def test_adv_cascading_deletion_competitor_level_isolation(self, db_session: Session):
        """
        Verify that deleting Competitor A cascades only Competitor A's sources and snapshots,
        leaving Competitor B and shared workspace scans intact.
        """
        user = User(name="Comp Iso User", email=f"comp_iso_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="Multi Comp WS", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp_a = Competitor(name="Comp A", workspace_id=ws.id)
        comp_b = Competitor(name="Comp B", workspace_id=ws.id)
        db_session.add_all([comp_a, comp_b])
        db_session.commit()

        src_a = Source(competitor_id=comp_a.id, name="Src A", url="https://a.com", source_type="website")
        src_b = Source(competitor_id=comp_b.id, name="Src B", url="https://b.com", source_type="website")
        db_session.add_all([src_a, src_b])
        db_session.commit()

        # Workspace-level scan with snapshots for both A and B
        ws_scan = ScanRun(workspace_id=ws.id, competitor_id=None, status="completed", total_sources=2)
        db_session.add(ws_scan)
        db_session.commit()

        snap_a = Snapshot(scan_run_id=ws_scan.id, source_id=src_a.id, status="success")
        snap_b = Snapshot(scan_run_id=ws_scan.id, source_id=src_b.id, status="success")
        db_session.add_all([snap_a, snap_b])
        db_session.commit()

        # Delete Competitor A
        db_session.delete(comp_a)
        db_session.commit()

        # Assert Comp A and Src A deleted
        assert db_session.query(Competitor).filter(Competitor.id == comp_a.id).first() is None
        assert db_session.query(Source).filter(Source.id == src_a.id).first() is None
        # Snap A was pointing to src_a, so it must be cascade deleted by source_id foreign key
        assert db_session.query(Snapshot).filter(Snapshot.id == snap_a.id).first() is None

        # Assert Comp B, Src B, Snap B, and ws_scan REMAIN INTACT
        assert db_session.query(Competitor).filter(Competitor.id == comp_b.id).first() is not None
        assert db_session.query(Source).filter(Source.id == src_b.id).first() is not None
        assert db_session.query(Snapshot).filter(Snapshot.id == snap_b.id).first() is not None
        assert db_session.query(ScanRun).filter(ScanRun.id == ws_scan.id).first() is not None

    def test_adv_cascading_deletion_source_level_isolation(self, db_session: Session):
        """
        Verify that deleting a single Source cascade-deletes only its snapshots,
        leaving its parent Competitor, Workspace, and other sources intact.
        """
        user = User(name="Src Iso User", email=f"src_iso_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="Src WS", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp = Competitor(name="Src Comp", workspace_id=ws.id)
        db_session.add(comp)
        db_session.commit()

        s1 = Source(competitor_id=comp.id, name="S1", url="https://s1.com", source_type="website")
        s2 = Source(competitor_id=comp.id, name="S2", url="https://s2.com", source_type="website")
        db_session.add_all([s1, s2])
        db_session.commit()

        scan = ScanRun(workspace_id=ws.id, competitor_id=comp.id, status="completed", total_sources=2)
        db_session.add(scan)
        db_session.commit()

        snap1 = Snapshot(scan_run_id=scan.id, source_id=s1.id, status="success")
        snap2 = Snapshot(scan_run_id=scan.id, source_id=s2.id, status="success")
        db_session.add_all([snap1, snap2])
        db_session.commit()

        # Delete source s1
        db_session.delete(s1)
        db_session.commit()

        assert db_session.query(Source).filter(Source.id == s1.id).first() is None
        assert db_session.query(Snapshot).filter(Snapshot.id == snap1.id).first() is None

        # s2 and snap2 remain
        assert db_session.query(Source).filter(Source.id == s2.id).first() is not None
        assert db_session.query(Snapshot).filter(Snapshot.id == snap2.id).first() is not None
        assert db_session.query(ScanRun).filter(ScanRun.id == scan.id).first() is not None

    def test_adv_cascading_deletion_user_level_full_purge(self, db_session: Session):
        """
        Verify that deleting a User cascades all the way down:
        User -> Workspace -> Competitor -> Source -> ScanRun -> Snapshot.
        Zero orphaned entities remain across the entire system.
        """
        user = User(name="Root User", email=f"root_{uuid.uuid4().hex[:8]}@example.com", password_hash="pw")
        db_session.add(user)
        db_session.commit()

        ws = Workspace(name="Root WS", user_id=user.id)
        db_session.add(ws)
        db_session.commit()

        comp = Competitor(name="Root Comp", workspace_id=ws.id)
        db_session.add(comp)
        db_session.commit()

        src = Source(competitor_id=comp.id, name="Root Src", url="https://root.com", source_type="website")
        db_session.add(src)
        db_session.commit()

        scan = ScanRun(workspace_id=ws.id, competitor_id=comp.id, status="completed", total_sources=1)
        db_session.add(scan)
        db_session.commit()

        snap = Snapshot(scan_run_id=scan.id, source_id=src.id, status="success")
        db_session.add(snap)
        db_session.commit()

        u_id = user.id
        ws_id = ws.id
        c_id = comp.id
        s_id = src.id
        sr_id = scan.id
        sn_id = snap.id

        # Delete user
        db_session.delete(user)
        db_session.commit()

        assert db_session.query(User).filter(User.id == u_id).first() is None
        assert db_session.query(Workspace).filter(Workspace.id == ws_id).first() is None
        assert db_session.query(Competitor).filter(Competitor.id == c_id).first() is None
        assert db_session.query(Source).filter(Source.id == s_id).first() is None
        assert db_session.query(ScanRun).filter(ScanRun.id == sr_id).first() is None
        assert db_session.query(Snapshot).filter(Snapshot.id == sn_id).first() is None

