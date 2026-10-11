# backend/tests/test_adapters.py
import pytest
import httpx
from unittest.mock import patch

from app.adapters.base import AdapterResult, BaseAdapter, DEFAULT_USER_AGENT
from app.adapters.hashing import compute_content_hash
from app.adapters.html_adapter import HtmlAdapter, _BoilerplateStripper
from app.adapters.rss_adapter import RssAdapter
from app.adapters.factory import get_adapter_for_source
from app.models.source import Source


# ============================================================================
# 1. Hashing Tests
# ============================================================================

def test_compute_content_hash_deterministic():
    text = "TradeCraft Competitive Intelligence"
    hash1 = compute_content_hash(text)
    hash2 = compute_content_hash(text)
    assert hash1 == hash2
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_compute_content_hash_empty_and_none():
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_content_hash("") == empty_hash
    assert compute_content_hash(None) == empty_hash


def test_compute_content_hash_different_inputs():
    hash1 = compute_content_hash("Feature A: Automated Ingestion")
    hash2 = compute_content_hash("Feature B: Automated Ingestion")
    assert hash1 != hash2


# ============================================================================
# 2. HTML Adapter Normalization & Determinism Tests
# ============================================================================

def test_html_normalization_identical_hash_across_dynamic_content():
    """
    Acceptance criterion: Two distinct HTML inputs with identical core text
    but different dynamic timestamps, scripts, and ads generate the exact same content hash.
    """
    html_a = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Competitor Alpha - Pricing</title>
        <script>
          window.analytics = { user: "12345", session: Date.now() };
        </script>
        <style>
          .banner { display: block; color: red; }
        </style>
      </head>
      <body>
        <header role="banner">
          <h1>Site Navigation</h1>
          <nav>
            <a href="/home">Home</a>
            <a href="/about">About</a>
          </nav>
        </header>

        <div class="ad-top-banner">
          <p>Black Friday Discount: 50% Off!</p>
        </div>

        <main>
          <h1>Enterprise Cloud Monitoring</h1>
          <p>Our flagship solution delivers real-time telemetry across distributed systems.</p>
          <div class="cookie-consent-modal">
            <p>We use cookies to improve your experience. Accept all?</p>
            <button>Accept</button>
          </div>
          <h2>Subscription Plans</h2>
          <p>Standard Tier: $49 per month.</p>
          <p>Enterprise Tier: Custom tailored billing.</p>
        </main>

        <aside>
          <h3>Related Articles</h3>
          <p>Read our recent blog posts.</p>
        </aside>

        <footer>
          <p>Generated at 2026-10-11 10:00:00 on server-prod-01</p>
          <p>&copy; 2026 Competitor Corp. All rights reserved.</p>
        </footer>
      </body>
    </html>
    """

    html_b = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Competitor Alpha - Pricing</title>
        <script>
          console.log("Different dynamic tracking code: " + Math.random());
        </script>
      </head>
      <body>
        <header>
          <nav>
            <a href="/login">Different Nav Items</a>
          </nav>
        </header>

        <div id="advertisement-slot-99">
          <span>Buy our enterprise addons now!</span>
        </div>

        <main>
          <h1>Enterprise Cloud Monitoring</h1>
          <p>  Our flagship solution delivers real-time telemetry across distributed systems.  </p>
          <div class="newsletter-popup">
            <p>Sign up for our newsletter to receive updates.</p>
          </div>
          <h2>Subscription Plans</h2>
          <p>Standard Tier: $49 per month.</p>
          <p>Enterprise Tier: Custom tailored billing.</p>
        </main>

        <footer>
          <p>Rendered at 2026-10-12 18:45:22 on worker-node-42</p>
        </footer>
      </body>
    </html>
    """

    adapter = HtmlAdapter(url="https://competitor.com/pricing")
    norm_a = adapter.normalize(html_a)
    norm_b = adapter.normalize(html_b)

    assert norm_a == norm_b
    assert "Enterprise Cloud Monitoring" in norm_a
    assert "Subscription Plans" in norm_a
    assert "Standard Tier: $49 per month." in norm_a

    # Noise must be absent
    assert "Black Friday Discount" not in norm_a
    assert "Site Navigation" not in norm_a
    assert "We use cookies" not in norm_a
    assert "Sign up for our newsletter" not in norm_a
    assert "Generated at 2026" not in norm_a
    assert "Rendered at 2026" not in norm_a

    # Content hashes must be strictly identical
    hash_a = compute_content_hash(norm_a)
    hash_b = compute_content_hash(norm_b)
    assert hash_a == hash_b


def test_html_normalization_handles_empty_and_whitespace():
    adapter = HtmlAdapter(url="https://example.com")
    assert adapter.normalize("") == ""
    assert adapter.normalize("   \n\t  ") == ""

    html_only_noise = """
    <html>
      <head><script>alert(1);</script></head>
      <body>
        <nav><a href="/">Link</a></nav>
        <div class="ad-banner">Ad</div>
        <footer>2026</footer>
      </body>
    </html>
    """
    assert adapter.normalize(html_only_noise) == ""


def test_html_normalization_void_elements_and_br():
    adapter = HtmlAdapter(url="https://example.com")
    html = """
    <div>
      Line One<br>Line Two<br/>Line Three
      <img src="test.jpg" alt="test">
      <hr>
      <input type="text" value="val">
    </div>
    """
    normalized = adapter.normalize(html)
    assert "Line One" in normalized
    assert "Line Two" in normalized
    assert "Line Three" in normalized


# ============================================================================
# 3. RSS / Atom Adapter Tests
# ============================================================================

def test_rss2_feed_normalization():
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Competitor Blog</title>
        <link>https://competitor.com/blog</link>
        <description>Product announcements and releases</description>
        <item>
          <title>Release v2.5 Announced</title>
          <link>https://competitor.com/blog/v2-5</link>
          <pubDate>Mon, 05 Oct 2026 12:00:00 GMT</pubDate>
          <description><![CDATA[<p>We are thrilled to announce <b>v2.5</b> with improved dashboard analytics.</p>]]></description>
        </item>
        <item>
          <title>Q3 Financial Results</title>
          <link>https://competitor.com/blog/q3-results</link>
          <pubDate>Sun, 04 Oct 2026 09:30:00 GMT</pubDate>
          <description>Record revenue in enterprise cloud solutions.</description>
        </item>
      </channel>
    </rss>
    """

    adapter = RssAdapter(url="https://competitor.com/blog/rss.xml")
    normalized = adapter.normalize(rss_xml)

    assert "Title: Release v2.5 Announced" in normalized
    assert "Link: https://competitor.com/blog/v2-5" in normalized
    assert "Published: Mon, 05 Oct 2026 12:00:00 GMT" in normalized
    assert "Summary: We are thrilled to announce v2.5 with improved dashboard analytics." in normalized
    assert "Title: Q3 Financial Results" in normalized
    assert "Link: https://competitor.com/blog/q3-results" in normalized
    assert "Summary: Record revenue in enterprise cloud solutions." in normalized
    assert "---" in normalized


def test_atom_feed_normalization():
    atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Competitor Atom Feed</title>
      <entry>
        <title>Security Advisory 2026-01</title>
        <link href="https://competitor.com/security/2026-01" />
        <updated>2026-10-09T14:00:00Z</updated>
        <summary>Patched a critical vulnerability in <a href="#">API authentication</a>.</summary>
      </entry>
    </feed>
    """

    adapter = RssAdapter(url="https://competitor.com/feed.atom")
    normalized = adapter.normalize(atom_xml)

    assert "Title: Security Advisory 2026-01" in normalized
    assert "Link: https://competitor.com/security/2026-01" in normalized
    assert "Published: 2026-10-09T14:00:00Z" in normalized
    assert "Summary: Patched a critical vulnerability in API authentication." in normalized


def test_rss_feed_empty_or_invalid():
    adapter = RssAdapter(url="https://competitor.com/feed")
    assert adapter.normalize("") == ""
    assert adapter.normalize("<invalid>xml content</broken") == ""


# ============================================================================
# 4. Adapter Factory Tests
# ============================================================================

def test_adapter_factory_by_source_type():
    src_rss = Source(
        id="src-1",
        competitor_id="comp-1",
        name="RSS Feed",
        url="https://example.com/updates",
        source_type="rss",
    )
    src_web = Source(
        id="src-2",
        competitor_id="comp-1",
        name="Main Site",
        url="https://example.com",
        source_type="website",
    )
    src_pricing = Source(
        id="src-3",
        competitor_id="comp-1",
        name="Pricing Page",
        url="https://example.com/pricing",
        source_type="pricing",
    )

    assert isinstance(get_adapter_for_source(src_rss), RssAdapter)
    assert isinstance(get_adapter_for_source(src_web), HtmlAdapter)
    assert isinstance(get_adapter_for_source(src_pricing), HtmlAdapter)


def test_adapter_factory_by_url_pattern():
    sources = [
        ("https://example.com/blog/feed.xml", RssAdapter),
        ("https://example.com/rss", RssAdapter),
        ("https://example.com/atom.xml", RssAdapter),
        ("https://example.com/news/feed/", RssAdapter),
        ("https://example.com/api?format=rss", RssAdapter),
        ("https://example.com/product/features", HtmlAdapter),
    ]

    for url, expected_cls in sources:
        src = {"url": url, "source_type": "other"}
        adapter = get_adapter_for_source(src)
        assert isinstance(adapter, expected_cls), f"URL {url} expected {expected_cls}, got {type(adapter)}"


# ============================================================================
# 5. Fault-Tolerant Network Fetch Tests (MockTransport)
# ============================================================================

@pytest.mark.anyio
async def test_html_adapter_fetch_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("user-agent") == DEFAULT_USER_AGENT
        html = "<html><body><h1>Clean Content</h1><p>Active paragraph.</p></body></html>"
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HtmlAdapter(url="https://example.com", client=client)
        result = await adapter.fetch()

        assert result.status == "success"
        assert result.http_status == 200
        assert "Clean Content" in result.normalized_content
        assert result.content_hash == compute_content_hash(result.normalized_content)
        assert result.error_message is None


@pytest.mark.anyio
async def test_html_adapter_fetch_404_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HtmlAdapter(url="https://example.com/missing", client=client)
        result = await adapter.fetch()

        assert result.status == "error"
        assert result.http_status == 404
        assert "HTTP 404: Not Found" in result.error_message
        assert result.normalized_content is None
        assert result.content_hash is None


@pytest.mark.anyio
async def test_html_adapter_fetch_403_forbidden():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HtmlAdapter(url="https://example.com/blocked", client=client)
        result = await adapter.fetch()

        assert result.status == "error"
        assert result.http_status == 403
        assert "HTTP 403: Forbidden" in result.error_message


@pytest.mark.anyio
async def test_html_adapter_fetch_500_server_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HtmlAdapter(url="https://example.com/error", client=client)
        result = await adapter.fetch()

        assert result.status == "error"
        assert result.http_status == 500
        assert "HTTP 500: Internal Server Error" in result.error_message


@pytest.mark.anyio
async def test_html_adapter_fetch_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Connection timed out after 15 seconds", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HtmlAdapter(url="https://example.com/timeout", client=client)
        result = await adapter.fetch()

        assert result.status == "error"
        assert result.http_status is None
        assert "request timeout" in result.error_message.lower()


@pytest.mark.anyio
async def test_html_adapter_fetch_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to resolve host", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = HtmlAdapter(url="https://unreachable-domain.test", client=client)
        result = await adapter.fetch()

        assert result.status == "error"
        assert result.http_status is None
        assert "network error" in result.error_message.lower()


@pytest.mark.anyio
async def test_rss_adapter_fetch_success():
    def handler(request: httpx.Request) -> httpx.Response:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Feed</title>
            <item>
              <title>Item 1</title>
              <link>https://example.com/1</link>
              <pubDate>2026-10-11</pubDate>
              <description>Summary 1</description>
            </item>
          </channel>
        </rss>
        """
        return httpx.Response(200, text=xml)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = RssAdapter(url="https://example.com/feed.xml", client=client)
        result = await adapter.fetch()

        assert result.status == "success"
        assert result.http_status == 200
        assert "Title: Item 1" in result.normalized_content
        assert result.content_hash == compute_content_hash(result.normalized_content)


@pytest.mark.anyio
async def test_rss_adapter_fetch_500_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = RssAdapter(url="https://example.com/feed.xml", client=client)
        result = await adapter.fetch()

        assert result.status == "error"
        assert result.http_status == 500
        assert "HTTP 500: Internal Server Error" in result.error_message


@pytest.mark.anyio
async def test_rss_adapter_fetch_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Feed timed out", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = RssAdapter(url="https://example.com/feed.xml", client=client)
        result = await adapter.fetch()

        assert result.status == "error"
        assert result.http_status is None
        assert "request timeout" in result.error_message.lower()


def test_html_normalization_with_bs4_mocked():
    import sys
    from unittest.mock import MagicMock

    mock_bs4 = MagicMock()
    mock_soup = MagicMock()
    mock_bs4.BeautifulSoup.return_value = mock_soup
    mock_soup.find_all.return_value = []
    mock_soup.return_value = []
    mock_soup.get_text.return_value = "Mocked BS4 Clean Content\nSecond Line"

    with patch.dict(sys.modules, {"bs4": mock_bs4}):
        adapter = HtmlAdapter("https://example.com")
        res = adapter.normalize("<html><body>Some content</body></html>")
        assert res == "Mocked BS4 Clean Content\nSecond Line"
        assert compute_content_hash(res) == compute_content_hash("Mocked BS4 Clean Content\nSecond Line")


def test_rss_normalization_with_feedparser_mocked():
    import sys
    from unittest.mock import MagicMock

    mock_feedparser = MagicMock()
    mock_feed = MagicMock()
    entry1 = {
        "title": "Mocked Post",
        "link": "https://example.com/mock",
        "published": "2026-10-11",
        "summary": "Mocked summary with <b>bold</b> text",
    }
    mock_feed.entries = [entry1]
    mock_feedparser.parse.return_value = mock_feed

    with patch.dict(sys.modules, {"feedparser": mock_feedparser}):
        adapter = RssAdapter("https://example.com/feed.xml")
        res = adapter.normalize("<xml>rss content</xml>")
        assert "Title: Mocked Post" in res
        assert "Link: https://example.com/mock" in res
        assert "Published: 2026-10-11" in res
        assert "Summary: Mocked summary with bold text" in res


def test_adapter_headers_and_defaults():
    html_adapter = HtmlAdapter("https://example.com")
    assert html_adapter.user_agent == DEFAULT_USER_AGENT
    assert "text/html" in html_adapter.get_headers()["Accept"]

    rss_adapter = RssAdapter("https://example.com/feed")
    assert rss_adapter.user_agent == DEFAULT_USER_AGENT
    assert "application/rss+xml" in rss_adapter.get_headers()["Accept"]
