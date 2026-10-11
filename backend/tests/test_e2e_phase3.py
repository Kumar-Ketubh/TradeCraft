# backend/tests/test_e2e_phase3.py
"""
Comprehensive Phase 3 End-to-End Test Suite (Tiers 1-4).
TradeCraft Data Collection & Snapshot Storage Engine.

Coverage Matrix:
- Tier 1: Feature Coverage (Models, Workspace Scan, Competitor Scan, Scans List, Snapshots History)
- Tier 2: Boundary & Corner Cases (Zero sources, Disabled monitoring, Empty/Huge HTML, Malformed RSS, Faults)
- Tier 3: Cross-Feature Combinations (Mixed source types, Mixed outcomes partial scan, Dynamic hash determinism, Content updates)
- Tier 4: Real-World Scenarios (Multi-tenant security isolation, Cascading deletion lifecycle, Full user journey)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy.orm import Session

from app.adapters.hashing import compute_content_hash
from app.core.security import get_password_hash
from app.models.competitor import Competitor
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.models.source import Source
from app.models.user import User
from app.models.workspace import Workspace


# ============================================================================
# Test Helpers & Mock Dispatcher
# ============================================================================

def create_user_and_headers(
    client,
    email: str = "e2e_user@example.com",
    name: str = "E2E Intelligence User",
    password: str = "StrongPassword123!",
) -> dict:
    """Register user and return authorization header."""
    res = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert res.status_code == 201, f"Failed to register user: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class E2EDispatcher:
    """
    Configurable HTTP response dispatcher for mock transport.
    Supports standard responses, fault injections, dynamic payload switching,
    and extreme boundary inputs.
    """

    def __init__(self):
        self.dynamic_pages = {}
        self.call_log = []

    def set_content(self, url: str, content: str):
        self.dynamic_pages[url] = content

    def __call__(self, url, *args, **kwargs):
        url_str = str(url)
        self.call_log.append(url_str)

        # 1. Dynamic override for content mutation testing
        if url_str in self.dynamic_pages:
            content = self.dynamic_pages[url_str]
            return httpx.Response(200, text=content, request=httpx.Request("GET", url_str))

        # 2. Error and fault injection based on URL patterns
        if "403" in url_str:
            return httpx.Response(403, text="Forbidden Access", request=httpx.Request("GET", url_str))
        elif "404" in url_str:
            return httpx.Response(404, text="Resource Not Found", request=httpx.Request("GET", url_str))
        elif "500" in url_str:
            return httpx.Response(500, text="Internal Server Error", request=httpx.Request("GET", url_str))
        elif "timeout" in url_str:
            raise httpx.ReadTimeout("Socket read timed out after 10.0s", request=httpx.Request("GET", url_str))
        elif "connect_error" in url_str:
            raise httpx.ConnectError("Connection refused by target host", request=httpx.Request("GET", url_str))

        # 3. Boundary & Extreme Content
        elif "empty_html" in url_str:
            return httpx.Response(200, text="", request=httpx.Request("GET", url_str))
        elif "whitespace_html" in url_str:
            return httpx.Response(200, text="\n\t  \r\n   \t  \n  ", request=httpx.Request("GET", url_str))
        elif "huge_html" in url_str:
            paragraphs = "".join(f"<p>Market update block #{i}: Rapid enterprise growth across sectors.</p>" for i in range(2500))
            huge_body = f"""<!DOCTYPE html><html><head><script>var ignore = 1;</script></head><body><h1>Huge Page</h1>{paragraphs}</body></html>"""
            return httpx.Response(200, text=huge_body, request=httpx.Request("GET", url_str))
        elif "malformed_rss" in url_str:
            broken_xml = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Broken Feed<item><title>Unclosed Tag<link>https://example.com</channel></rss>"""
            return httpx.Response(200, text=broken_xml, request=httpx.Request("GET", url_str))
        elif "empty_rss" in url_str:
            return httpx.Response(200, text="", request=httpx.Request("GET", url_str))
        elif "empty_channel_rss" in url_str:
            empty_feed = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Empty News</title><link>https://news.example.com</link></channel></rss>"""
            return httpx.Response(200, text=empty_feed, request=httpx.Request("GET", url_str))

        # 4. Standard RSS feed
        elif "rss" in url_str or "feed" in url_str or url_str.endswith(".xml"):
            feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>Apex Intelligence Feed</title>
                    <link>https://apex.example.com</link>
                    <item>
                        <title>Release 4.0: Machine Vision Capabilities</title>
                        <link>https://apex.example.com/news/v4</link>
                        <description>Announcing breakthrough automated scanning.</description>
                    </item>
                </channel>
            </rss>"""
            return httpx.Response(200, text=feed_xml, request=httpx.Request("GET", url_str))

        # 5. Standard Website / HTML
        else:
            std_html = f"""<!DOCTYPE html>
            <html>
                <head>
                    <title>TradeCraft Target Site</title>
                    <script>console.log("analytics tracking");</script>
                    <style>.hidden {{ display: none; }}</style>
                </head>
                <body>
                    <header><nav><a href="/">Home</a></nav></header>
                    <main>
                        <h1>Competitive Intelligence Matrix</h1>
                        <p>Real-time analytics and strategic signals for {url_str}.</p>
                    </main>
                    <footer><p>&copy; 2026 Target Corp.</p></footer>
                </body>
            </html>"""
            return httpx.Response(200, text=std_html, request=httpx.Request("GET", url_str))


# ============================================================================
# TIER 1: Feature Coverage (Opaque-box E2E)
# ============================================================================

def test_tier1_scan_run_and_snapshot_model_attributes_and_relationships(db_session: Session):
    """
    Tier 1 - Feature Coverage:
    Verify model definition, attribute persistence, foreign keys, and bidirectional ORM
    relationships for ScanRun and Snapshot with cascade behaviors.
    """
    # 1. Create base entities directly in DB
    user = User(
        name="ORM Tester",
        email="orm_tester@example.com",
        password_hash=get_password_hash("password123"),
    )
    db_session.add(user)
    db_session.commit()

    workspace = Workspace(name="ORM Workspace", user_id=user.id)
    db_session.add(workspace)
    db_session.commit()

    competitor = Competitor(
        name="Rival Systems",
        workspace_id=workspace.id,
        website="https://rival.example.com",
        monitoring_enabled=True,
    )
    db_session.add(competitor)
    db_session.commit()

    source = Source(
        name="Rival Core API",
        url="https://rival.example.com/api",
        competitor_id=competitor.id,
        source_type="website",
        monitoring_enabled=True,
    )
    db_session.add(source)
    db_session.commit()

    # 2. Instantiate and persist ScanRun
    now = datetime.now(timezone.utc)
    scan_run = ScanRun(
        workspace_id=workspace.id,
        competitor_id=competitor.id,
        status="completed",
        total_sources=1,
        successful_sources=1,
        failed_sources=0,
        error_message=None,
        created_at=now,
        completed_at=now,
    )
    db_session.add(scan_run)
    db_session.commit()
    db_session.refresh(scan_run)

    assert scan_run.id is not None
    assert len(scan_run.id) == 36  # UUID string format
    assert scan_run.workspace_id == workspace.id
    assert scan_run.competitor_id == competitor.id
    assert scan_run.status == "completed"

    # 3. Instantiate and persist Snapshot
    raw_text = "<html><body><h1>Direct Model Test</h1></body></html>"
    norm_text = "Direct Model Test"
    content_hash = compute_content_hash(norm_text)

    snapshot = Snapshot(
        scan_run_id=scan_run.id,
        source_id=source.id,
        status="success",
        status_code=200,
        raw_content=raw_text,
        normalized_content=norm_text,
        content_hash=content_hash,
        error_message=None,
        headers={"content-type": "text/html"},
        response_time_ms=145,
        created_at=now,
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    assert snapshot.id is not None
    assert len(snapshot.id) == 36
    assert snapshot.content_hash == content_hash
    assert len(snapshot.content_hash) == 64
    assert snapshot.response_time_ms == 145

    # 4. Verify bidirectional relationships
    assert snapshot.scan_run.id == scan_run.id
    assert snapshot.source.id == source.id
    assert scan_run.workspace.id == workspace.id
    assert scan_run.competitor.id == competitor.id
    assert len(scan_run.snapshots) == 1
    assert scan_run.snapshots[0].id == snapshot.id
    assert len(source.snapshots) == 1
    assert source.snapshots[0].id == snapshot.id
    assert scan_run in workspace.scan_runs
    assert scan_run in competitor.scan_runs

    # 5. Verify ScanRun deletion cascades to Snapshot without deleting the Source
    db_session.delete(scan_run)
    db_session.commit()

    assert db_session.query(ScanRun).filter(ScanRun.id == scan_run.id).first() is None
    assert db_session.query(Snapshot).filter(Snapshot.id == snapshot.id).first() is None
    # Source must remain intact
    assert db_session.query(Source).filter(Source.id == source.id).first() is not None


def test_tier1_single_workspace_scan_execution_with_multiple_sources(client):
    """
    Tier 1 - Feature Coverage:
    Trigger a full workspace scan with multiple competitors and multiple source types.
    Verify response structure, status, counts, and detail snapshots.
    """
    headers = create_user_and_headers(client, "tier1_ws_scan@example.com")
    ws_res = client.post("/workspaces", json={"name": "Tier 1 Enterprise Market"}, headers=headers)
    ws_id = ws_res.json()["id"]

    # Competitor 1 with 2 sources
    comp1 = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Alpha Corp", "website": "https://alpha.example.com"},
        headers=headers,
    ).json()
    client.post(
        f"/competitors/{comp1['id']}/sources",
        json={"name": "Alpha Web", "url": "https://alpha.example.com", "source_type": "website"},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp1['id']}/sources",
        json={"name": "Alpha News", "url": "https://alpha.example.com/rss.xml", "source_type": "rss"},
        headers=headers,
    )

    # Competitor 2 with 2 sources
    comp2 = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Beta Dynamics", "website": "https://beta.example.com"},
        headers=headers,
    ).json()
    client.post(
        f"/competitors/{comp2['id']}/sources",
        json={"name": "Beta Pricing", "url": "https://beta.example.com/pricing", "source_type": "pricing"},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp2['id']}/sources",
        json={"name": "Beta Blog", "url": "https://beta.example.com/feed", "source_type": "rss"},
        headers=headers,
    )

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan_data = scan_res.json()
    assert scan_data["workspace_id"] == ws_id
    assert scan_data["competitor_id"] is None
    assert scan_data["status"] == "completed"
    assert scan_data["total_sources"] == 4
    assert scan_data["successful_sources"] == 4
    assert scan_data["failed_sources"] == 0
    assert scan_data["error_message"] is None
    assert scan_data["scan_run_id"] == scan_data["id"]
    assert scan_data["completed_at"] is not None

    # Retrieve scan detail
    scan_id = scan_data["id"]
    detail_res = client.get(f"/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == scan_id
    assert len(detail["snapshots"]) == 4

    for snap in detail["snapshots"]:
        assert snap["scan_run_id"] == scan_id
        assert snap["status"] == "success"
        assert snap["status_code"] == 200
        assert snap["content_hash"] is not None
        assert len(snap["content_hash"]) == 64
        assert snap["normalized_content"] is not None


def test_tier1_single_competitor_scan_execution(client):
    """
    Tier 1 - Feature Coverage:
    Trigger a scan targeting a single competitor. Verify that only sources belonging
    to that competitor are scanned and persisted.
    """
    headers = create_user_and_headers(client, "tier1_comp_scan@example.com")
    ws = client.post("/workspaces", json={"name": "Targeted Sector"}, headers=headers).json()
    ws_id = ws["id"]

    comp_a = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Competitor A"},
        headers=headers,
    ).json()
    comp_b = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Competitor B"},
        headers=headers,
    ).json()

    # Comp A has 2 sources
    client.post(
        f"/competitors/{comp_a['id']}/sources",
        json={"name": "A-1", "url": "https://a.com/page1", "source_type": "website"},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp_a['id']}/sources",
        json={"name": "A-2", "url": "https://a.com/feed.xml", "source_type": "rss"},
        headers=headers,
    )
    # Comp B has 1 source
    client.post(
        f"/competitors/{comp_b['id']}/sources",
        json={"name": "B-1", "url": "https://b.com/page", "source_type": "website"},
        headers=headers,
    )

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/competitors/{comp_a['id']}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan_data = scan_res.json()
    assert scan_data["workspace_id"] == ws_id
    assert scan_data["competitor_id"] == comp_a["id"]
    assert scan_data["total_sources"] == 2
    assert scan_data["successful_sources"] == 2
    assert scan_data["status"] == "completed"

    # Detail view confirms only Comp A snapshots exist for this scan
    detail_res = client.get(f"/scans/{scan_data['id']}", headers=headers)
    assert detail_res.status_code == 200
    snapshots = detail_res.json()["snapshots"]
    assert len(snapshots) == 2


def test_tier1_list_workspace_scans_returns_newest_first(client):
    """
    Tier 1 - Feature Coverage:
    List scans for a workspace and verify that scans are ordered in descending
    chronological order.
    """
    headers = create_user_and_headers(client, "tier1_list_scans@example.com")
    ws = client.post("/workspaces", json={"name": "History WS"}, headers=headers).json()
    ws_id = ws["id"]
    comp = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Comp Chrono"}, headers=headers).json()
    client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Chrono Web", "url": "https://chrono.example.com", "source_type": "website"},
        headers=headers,
    )

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        res1 = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
        res2 = client.post(f"/competitors/{comp['id']}/scan", headers=headers)
        res3 = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res3.status_code == 201

    list_res = client.get(f"/workspaces/{ws_id}/scans", headers=headers)
    assert list_res.status_code == 200
    scans = list_res.json()
    assert len(scans) == 3

    # Check descending order by created_at
    for i in range(len(scans) - 1):
        assert scans[i]["created_at"] >= scans[i + 1]["created_at"]

    # Verify attributes
    for s in scans:
        assert s["workspace_id"] == ws_id
        assert "status" in s
        assert "total_sources" in s
        assert "successful_sources" in s
        assert "scan_run_id" in s


def test_tier1_source_snapshot_history_retrieval_and_order(client):
    """
    Tier 1 - Feature Coverage:
    Verify retrieval of snapshots for an individual source, ordered newest first.
    """
    headers = create_user_and_headers(client, "tier1_source_history@example.com")
    ws = client.post("/workspaces", json={"name": "Snap History WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "History Corp"}, headers=headers).json()
    src = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Target Feed", "url": "https://history.example.com/feed.xml", "source_type": "rss"},
        headers=headers,
    ).json()
    src_id = src["id"]

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        client.post(f"/workspaces/{ws['id']}/scan", headers=headers)
        client.post(f"/competitors/{comp['id']}/scan", headers=headers)

    snap_res = client.get(f"/sources/{src_id}/snapshots", headers=headers)
    assert snap_res.status_code == 200
    snapshots = snap_res.json()
    assert len(snapshots) == 2
    assert snapshots[0]["source_id"] == src_id
    assert snapshots[1]["source_id"] == src_id
    assert snapshots[0]["created_at"] >= snapshots[1]["created_at"]
    assert snapshots[0]["status"] == "success"
    assert snapshots[0]["status_code"] == 200


# ============================================================================
# TIER 2: Boundary & Corner Cases
# ============================================================================

def test_tier2_scan_zero_competitors_or_zero_sources(client):
    """
    Tier 2 - Boundary:
    Trigger scans when zero competitors exist or when competitors have zero sources.
    Must return status 'completed' with total_sources=0 immediately.
    """
    headers = create_user_and_headers(client, "tier2_zeros@example.com")
    ws = client.post("/workspaces", json={"name": "Empty Space"}, headers=headers).json()
    ws_id = ws["id"]

    # 1. Scan workspace with 0 competitors
    res1 = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["total_sources"] == 0
    assert data1["successful_sources"] == 0
    assert data1["failed_sources"] == 0
    assert data1["status"] == "completed"
    assert data1["completed_at"] is not None

    # 2. Add competitor with 0 sources and scan competitor
    comp = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Void Corp"}, headers=headers).json()
    comp_id = comp["id"]

    res2 = client.post(f"/competitors/{comp_id}/scan", headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["total_sources"] == 0
    assert data2["status"] == "completed"
    assert data2["completed_at"] is not None

    # 3. Scan workspace that has competitor but 0 sources
    res3 = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
    assert res3.status_code == 201
    data3 = res3.json()
    assert data3["total_sources"] == 0
    assert data3["status"] == "completed"


def test_tier2_competitor_monitoring_disabled_excluded_from_workspace_scan(client):
    """
    Tier 2 - Boundary:
    Competitor with monitoring_enabled=False must have all its sources excluded
    from a workspace-wide scan.
    """
    headers = create_user_and_headers(client, "tier2_comp_disabled@example.com")
    ws = client.post("/workspaces", json={"name": "Disabled Filter WS"}, headers=headers).json()
    ws_id = ws["id"]

    # Active competitor
    comp_active = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Active Comp", "monitoring_enabled": True},
        headers=headers,
    ).json()
    client.post(
        f"/competitors/{comp_active['id']}/sources",
        json={"name": "Active Source", "url": "https://active.example.com", "monitoring_enabled": True},
        headers=headers,
    )

    # Inactive competitor
    comp_inactive = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Inactive Comp", "monitoring_enabled": False},
        headers=headers,
    ).json()
    client.post(
        f"/competitors/{comp_inactive['id']}/sources",
        json={"name": "Inactive Source", "url": "https://inactive.example.com", "monitoring_enabled": True},
        headers=headers,
    )

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    assert scan_res.status_code == 201
    data = scan_res.json()
    # Exactly 1 source should have been scanned
    assert data["total_sources"] == 1
    assert data["successful_sources"] == 1

    detail = client.get(f"/scans/{data['id']}", headers=headers).json()
    assert len(detail["snapshots"]) == 1


def test_tier2_source_monitoring_disabled_excluded_from_scans(client):
    """
    Tier 2 - Boundary:
    Source with monitoring_enabled=False must be excluded from both workspace
    and competitor scans.
    """
    headers = create_user_and_headers(client, "tier2_src_disabled@example.com")
    ws = client.post("/workspaces", json={"name": "Source Filter WS"}, headers=headers).json()
    ws_id = ws["id"]
    comp = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Filter Comp"}, headers=headers).json()
    comp_id = comp["id"]

    # 1 enabled source, 1 disabled source
    client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Active Page", "url": "https://filter.com/on", "monitoring_enabled": True},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Paused Page", "url": "https://filter.com/off", "monitoring_enabled": False},
        headers=headers,
    )

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        # Competitor scan test
        res_comp = client.post(f"/competitors/{comp_id}/scan", headers=headers)
        assert res_comp.status_code == 201
        assert res_comp.json()["total_sources"] == 1

        # Workspace scan test
        res_ws = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
        assert res_ws.status_code == 201
        assert res_ws.json()["total_sources"] == 1


def test_tier2_html_normalization_empty_whitespace_and_huge_content(client):
    """
    Tier 2 - Boundary:
    Test normalization edge cases:
    - Empty HTML payload
    - Extreme whitespace payload
    - Large 200KB+ HTML payload with scripts and styles
    """
    headers = create_user_and_headers(client, "tier2_extreme_html@example.com")
    ws = client.post("/workspaces", json={"name": "Extreme HTML WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Extreme Corp"}, headers=headers).json()

    s_empty = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Empty Page", "url": "https://extreme.com/empty_html", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s_ws = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Whitespace Page", "url": "https://extreme.com/whitespace_html", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s_huge = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Huge Page", "url": "https://extreme.com/huge_html", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan_id = scan_res.json()["id"]

    detail = client.get(f"/scans/{scan_id}", headers=headers).json()
    snapshots_by_src = {s["source_id"]: s for s in detail["snapshots"]}

    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # Empty payload
    assert snapshots_by_src[s_empty]["status"] == "success"
    assert snapshots_by_src[s_empty]["normalized_content"] == ""
    assert snapshots_by_src[s_empty]["content_hash"] == empty_hash

    # Whitespace payload
    assert snapshots_by_src[s_ws]["status"] == "success"
    assert snapshots_by_src[s_ws]["normalized_content"] == ""
    assert snapshots_by_src[s_ws]["content_hash"] == empty_hash

    # Huge payload
    assert snapshots_by_src[s_huge]["status"] == "success"
    assert "Market update block" in snapshots_by_src[s_huge]["normalized_content"]
    assert "ignore" not in snapshots_by_src[s_huge]["normalized_content"]  # script stripped
    assert len(snapshots_by_src[s_huge]["content_hash"]) == 64


def test_tier2_malformed_and_empty_rss_feed_handling(client):
    """
    Tier 2 - Boundary:
    Test RSS adapter fault-tolerance with malformed XML feeds, empty feeds,
    and feeds with zero entries.
    """
    headers = create_user_and_headers(client, "tier2_rss_boundary@example.com")
    ws = client.post("/workspaces", json={"name": "RSS Boundary WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "RSS Edge Corp"}, headers=headers).json()

    s_malformed = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Malformed RSS", "url": "https://rss.edge/malformed_rss", "source_type": "rss"},
        headers=headers,
    ).json()["id"]

    s_empty = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Empty RSS", "url": "https://rss.edge/empty_rss", "source_type": "rss"},
        headers=headers,
    ).json()["id"]

    s_zero_items = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Zero Items RSS", "url": "https://rss.edge/empty_channel_rss", "source_type": "rss"},
        headers=headers,
    ).json()["id"]

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan_id = scan_res.json()["id"]
    detail = client.get(f"/scans/{scan_id}", headers=headers).json()
    snapshots_by_src = {s["source_id"]: s for s in detail["snapshots"]}

    # All three must produce persisted snapshots without crashing
    assert snapshots_by_src[s_malformed]["status"] == "success"
    assert snapshots_by_src[s_empty]["status"] == "success"
    assert snapshots_by_src[s_zero_items]["status"] == "success"


def test_tier2_error_snapshot_recording_for_all_http_and_network_failures(client):
    """
    Tier 2 - Boundary:
    Verify that 403 Forbidden, 404 Not Found, 500 Server Error, Read Timeout,
    and Connect Error all generate persisted error snapshots without crashing.
    """
    headers = create_user_and_headers(client, "tier2_all_errors@example.com")
    ws = client.post("/workspaces", json={"name": "Failure Matrix WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Broken Target Corp"}, headers=headers).json()

    sources = {
        "403": client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "Protected 403", "url": "https://broken.com/403", "source_type": "website"},
            headers=headers,
        ).json()["id"],
        "404": client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "Missing 404", "url": "https://broken.com/404", "source_type": "website"},
            headers=headers,
        ).json()["id"],
        "500": client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "Crash 500", "url": "https://broken.com/500", "source_type": "website"},
            headers=headers,
        ).json()["id"],
        "timeout": client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "Timeout Route", "url": "https://broken.com/timeout", "source_type": "website"},
            headers=headers,
        ).json()["id"],
        "connect_error": client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "Unreachable", "url": "https://broken.com/connect_error", "source_type": "website"},
            headers=headers,
        ).json()["id"],
    }

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan = scan_res.json()
    assert scan["status"] == "failed"
    assert scan["total_sources"] == 5
    assert scan["successful_sources"] == 0
    assert scan["failed_sources"] == 5
    assert "All 5 sources failed" in scan["error_message"]

    detail = client.get(f"/scans/{scan['id']}", headers=headers).json()
    snaps = {s["source_id"]: s for s in detail["snapshots"]}

    # Verify 403
    s403 = snaps[sources["403"]]
    assert s403["status"] == "error"
    assert s403["status_code"] == 403
    assert "403" in s403["error_message"]

    # Verify 404
    s404 = snaps[sources["404"]]
    assert s404["status"] == "error"
    assert s404["status_code"] == 404
    assert "404" in s404["error_message"]

    # Verify 500
    s500 = snaps[sources["500"]]
    assert s500["status"] == "error"
    assert s500["status_code"] == 500
    assert "500" in s500["error_message"]

    # Verify Timeout
    stimeout = snaps[sources["timeout"]]
    assert stimeout["status"] == "error"
    assert stimeout["status_code"] is None
    assert "timed out" in stimeout["error_message"].lower()

    # Verify Connect Error
    sconn = snaps[sources["connect_error"]]
    assert sconn["status"] == "error"
    assert sconn["status_code"] is None
    assert "connection" in sconn["error_message"].lower()


# ============================================================================
# TIER 3: Cross-Feature Combinations (Pairwise & Interactions)
# ============================================================================

def test_tier3_mixed_sources_in_single_workspace(client):
    """
    Tier 3 - Pairwise / Interaction:
    Single workspace with concurrent scan across website, rss, and pricing sources.
    Verify all adapter types execute concurrently and produce correct normalized output.
    """
    headers = create_user_and_headers(client, "tier3_mixed_types@example.com")
    ws = client.post("/workspaces", json={"name": "Mixed Sources WS"}, headers=headers).json()
    ws_id = ws["id"]
    comp = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Omni Rival"}, headers=headers).json()

    s_web = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Main Site", "url": "https://omni.com/home", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s_rss = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "News Feed", "url": "https://omni.com/feed.xml", "source_type": "rss"},
        headers=headers,
    ).json()["id"]

    s_pricing = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Pricing Grid", "url": "https://omni.com/pricing", "source_type": "pricing"},
        headers=headers,
    ).json()["id"]

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan = scan_res.json()
    assert scan["status"] == "completed"
    assert scan["total_sources"] == 3
    assert scan["successful_sources"] == 3
    assert scan["failed_sources"] == 0

    detail = client.get(f"/scans/{scan['id']}", headers=headers).json()
    snaps = {s["source_id"]: s for s in detail["snapshots"]}

    assert snaps[s_web]["status"] == "success"
    assert snaps[s_rss]["status"] == "success"
    assert snaps[s_pricing]["status"] == "success"
    # RSS should have feed item summary
    assert "Release 4.0" in snaps[s_rss]["normalized_content"]


def test_tier3_mixed_outcomes_partial_scan_completion(client):
    """
    Tier 3 - Pairwise / Interaction:
    Scan with mixed outcomes:
    1 successful HTML source, 1 successful RSS source, 1 404 failure, 1 timeout failure.
    Must mark scan as 'partial', record total_sources=4, successful=2, failed=2,
    and persist all 4 snapshots.
    """
    headers = create_user_and_headers(client, "tier3_partial@example.com")
    ws = client.post("/workspaces", json={"name": "Partial WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Partial Corp"}, headers=headers).json()

    s1_html_ok = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "HTML OK", "url": "https://partial.com/page", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s2_rss_ok = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "RSS OK", "url": "https://partial.com/feed.xml", "source_type": "rss"},
        headers=headers,
    ).json()["id"]

    s3_404_fail = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "404 Fail", "url": "https://partial.com/404", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s4_timeout_fail = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Timeout Fail", "url": "https://partial.com/timeout", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_res = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan = scan_res.json()
    assert scan["status"] == "partial"
    assert scan["total_sources"] == 4
    assert scan["successful_sources"] == 2
    assert scan["failed_sources"] == 2
    assert "2 of 4 sources failed to fetch" in scan["error_message"]

    detail = client.get(f"/scans/{scan['id']}", headers=headers).json()
    assert len(detail["snapshots"]) == 4

    snaps = {s["source_id"]: s for s in detail["snapshots"]}
    assert snaps[s1_html_ok]["status"] == "success"
    assert snaps[s2_rss_ok]["status"] == "success"
    assert snaps[s3_404_fail]["status"] == "error"
    assert snaps[s4_timeout_fail]["status"] == "error"


def test_tier3_content_change_detection_across_consecutive_scans(client):
    """
    Tier 3 - Pairwise / Interaction:
    Verify content change detection across consecutive scans:
    - Scan 1: captures source with Hash A.
    - Source content changes.
    - Scan 2: captures updated source with distinct Hash B.
    - Historical endpoint shows distinct hashes and progression.
    """
    headers = create_user_and_headers(client, "tier3_change_detection@example.com")
    ws = client.post("/workspaces", json={"name": "Change Detection WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Dynamic Rival"}, headers=headers).json()
    target_url = "https://dynamic.example.com/pricing"
    src = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Pricing Source", "url": target_url, "source_type": "website"},
        headers=headers,
    ).json()
    src_id = src["id"]

    dispatcher = E2EDispatcher()

    # Step 1: Initial scan with version 1 content
    v1_content = """<html><body><h1>Enterprise Plan</h1><p>Price: $99 / mo</p></body></html>"""
    dispatcher.set_content(target_url, v1_content)

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        res1 = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)
    assert res1.status_code == 201
    scan1_id = res1.json()["id"]

    snap1 = client.get(f"/scans/{scan1_id}", headers=headers).json()["snapshots"][0]
    hash1 = snap1["content_hash"]
    assert "Price: $99 / mo" in snap1["normalized_content"]

    # Step 2: Source content mutates (competitor raised price)
    v2_content = """<html><body><h1>Enterprise Plan</h1><p>Price: $149 / mo (Updated Q4)</p></body></html>"""
    dispatcher.set_content(target_url, v2_content)

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        res2 = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)
    assert res2.status_code == 201
    scan2_id = res2.json()["id"]

    snap2 = client.get(f"/scans/{scan2_id}", headers=headers).json()["snapshots"][0]
    hash2 = snap2["content_hash"]
    assert "Price: $149 / mo" in snap2["normalized_content"]

    # Step 3: Assert distinct content hashes generated
    assert hash1 != hash2

    # Step 4: Verify snapshot history reflects both snapshots
    hist_res = client.get(f"/sources/{src_id}/snapshots", headers=headers)
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert len(hist) == 2
    assert hist[0]["content_hash"] == hash2  # newest
    assert hist[1]["content_hash"] == hash1  # previous


def test_tier3_unchanged_content_preserves_deterministic_hash_across_dynamic_updates(client):
    """
    Tier 3 - Pairwise / Interaction:
    Verify that dynamic changes outside core content (e.g. ad banners, session tokens,
    cookie modals, timestamps) produce the identical SHA-256 hash across scans.
    """
    headers = create_user_and_headers(client, "tier3_hash_determinism@example.com")
    ws = client.post("/workspaces", json={"name": "Deterministic Hash WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Stable Corp"}, headers=headers).json()
    target_url = "https://stable.example.com/product"
    src = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Product Page", "url": target_url, "source_type": "website"},
        headers=headers,
    ).json()

    dispatcher = E2EDispatcher()

    # Scan 1: Initial view with session A and timestamp A
    html_1 = """
    <!DOCTYPE html>
    <html>
        <head>
            <script>window.session = "SESSION_111111";</script>
            <style>.promo { color: red; }</style>
        </head>
        <body>
            <nav><a href="/link1">Nav 1</a></nav>
            <div class="ad-banner">Flash Sale 10% Off!</div>
            <main>
                <h1>Core Product Specification</h1>
                <p>Enterprise cloud-native competitive analysis engine.</p>
            </main>
            <footer>Server: prod-us-east-1, Rendered at: 10:00:00 UTC</footer>
        </body>
    </html>
    """
    dispatcher.set_content(target_url, html_1)

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        r1 = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)
    scan1_id = r1.json()["id"]
    snap1 = client.get(f"/scans/{scan1_id}", headers=headers).json()["snapshots"][0]
    hash1 = snap1["content_hash"]

    # Scan 2: Subsequent view with session B, ad banner B, and timestamp B
    html_2 = """
    <!DOCTYPE html>
    <html>
        <head>
            <script>window.session = "SESSION_999999_DIFFERENT";</script>
            <style>.promo { color: blue; }</style>
        </head>
        <body>
            <nav><a href="/link2">Nav 2</a></nav>
            <div class="cookie-banner">Please consent to tracking cookies.</div>
            <main>
                <h1>Core Product Specification</h1>
                <p>Enterprise cloud-native competitive analysis engine.</p>
            </main>
            <footer>Server: prod-eu-west-1, Rendered at: 16:45:30 UTC</footer>
        </body>
    </html>
    """
    dispatcher.set_content(target_url, html_2)

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        r2 = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)
    scan2_id = r2.json()["id"]
    snap2 = client.get(f"/scans/{scan2_id}", headers=headers).json()["snapshots"][0]
    hash2 = snap2["content_hash"]

    # Normalization must strip all boilerplate and dynamic metadata
    assert hash1 == hash2
    assert snap1["normalized_content"] == snap2["normalized_content"]
    assert "Core Product Specification" in snap1["normalized_content"]
    assert "Flash Sale" not in snap1["normalized_content"]
    assert "SESSION" not in snap1["normalized_content"]


# ============================================================================
# TIER 4: Real-World Application Scenarios (Workloads & Security)
# ============================================================================

def test_tier4_multi_tenant_security_isolation_matrix(client):
    """
    Tier 4 - Real-World Scenario:
    Multi-tenant isolation matrix between User A and User B.
    Ensure User B cannot scan, view, list, or access User A's workspaces,
    competitors, scan runs, or snapshots across all endpoints (404 isolation).
    Also verify 401 unauthenticated enforcement.
    """
    # Setup User A with resources
    headers_a = create_user_and_headers(client, "user_a_owner@example.com", name="User A")
    ws_a = client.post("/workspaces", json={"name": "User A Workspace"}, headers=headers_a).json()["id"]
    comp_a = client.post(
        f"/workspaces/{ws_a}/competitors",
        json={"name": "Competitor A"},
        headers=headers_a,
    ).json()["id"]
    src_a = client.post(
        f"/competitors/{comp_a}/sources",
        json={"name": "Source A", "url": "https://a.com/page", "source_type": "website"},
        headers=headers_a,
    ).json()["id"]

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_a_res = client.post(f"/workspaces/{ws_a}/scan", headers=headers_a)
    scan_a_id = scan_a_res.json()["id"]

    # Setup User B
    headers_b = create_user_and_headers(client, "user_b_tenant@example.com", name="User B")
    ws_b = client.post("/workspaces", json={"name": "User B Workspace"}, headers=headers_b).json()["id"]

    # 1. User B attempts to trigger scan on User A's workspace -> 404
    res1 = client.post(f"/workspaces/{ws_a}/scan", headers=headers_b)
    assert res1.status_code == 404
    assert "not found" in res1.json()["detail"].lower()

    # 2. User B attempts to trigger scan on User A's competitor -> 404
    res2 = client.post(f"/competitors/{comp_a}/scan", headers=headers_b)
    assert res2.status_code == 404
    assert "not found" in res2.json()["detail"].lower()

    # 3. User B attempts to list scans for User A's workspace -> 404
    res3 = client.get(f"/workspaces/{ws_a}/scans", headers=headers_b)
    assert res3.status_code == 404
    assert "not found" in res3.json()["detail"].lower()

    # 4. User B attempts to view User A's scan detail -> 404
    res4 = client.get(f"/scans/{scan_a_id}", headers=headers_b)
    assert res4.status_code == 404
    assert "not found" in res4.json()["detail"].lower()

    # 5. User B attempts to view snapshots for User A's source -> 404
    res5 = client.get(f"/sources/{src_a}/snapshots", headers=headers_b)
    assert res5.status_code == 404
    assert "not found" in res5.json()["detail"].lower()

    # 6. Unauthenticated requests receive 401 Unauthorized across all 5 endpoints
    assert client.post(f"/workspaces/{ws_a}/scan").status_code == 401
    assert client.post(f"/competitors/{comp_a}/scan").status_code == 401
    assert client.get(f"/workspaces/{ws_a}/scans").status_code == 401
    assert client.get(f"/scans/{scan_a_id}").status_code == 401
    assert client.get(f"/sources/{src_a}/snapshots").status_code == 401

    # 7. User B scans own workspace successfully and sees only own scans
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        scan_b_res = client.post(f"/workspaces/{ws_b}/scan", headers=headers_b)
    assert scan_b_res.status_code == 201

    b_scans = client.get(f"/workspaces/{ws_b}/scans", headers=headers_b).json()
    assert len(b_scans) == 1
    assert b_scans[0]["workspace_id"] == ws_b


def test_tier4_full_cascading_deletion_lifecycle(client, db_session: Session):
    """
    Tier 4 - Real-World Scenario:
    Full cascading deletion lifecycle test:
    Workspace -> Competitor -> Source -> ScanRun -> Snapshot.
    Verify that deleting an entity cleanly wipes all associated downstream child
    records without leaving orphan entries in the database.
    """
    headers = create_user_and_headers(client, "tier4_cascade@example.com")
    ws_res = client.post("/workspaces", json={"name": "Cascade Root WS"}, headers=headers)
    ws_id = ws_res.json()["id"]

    # Competitor 1 with 2 sources
    comp1 = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Cascade Comp 1"}, headers=headers).json()
    comp1_id = comp1["id"]
    s1 = client.post(
        f"/competitors/{comp1_id}/sources",
        json={"name": "Source 1", "url": "https://casc.com/1", "source_type": "website"},
        headers=headers,
    ).json()["id"]
    s2 = client.post(
        f"/competitors/{comp1_id}/sources",
        json={"name": "Source 2", "url": "https://casc.com/2", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    # Competitor 2 with 1 source
    comp2 = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Cascade Comp 2"}, headers=headers).json()
    comp2_id = comp2["id"]
    s3 = client.post(
        f"/competitors/{comp2_id}/sources",
        json={"name": "Source 3", "url": "https://casc.com/3", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        # 1. Trigger workspace scan (3 snapshots)
        ws_scan = client.post(f"/workspaces/{ws_id}/scan", headers=headers).json()
        ws_scan_id = ws_scan["id"]

        # 2. Trigger competitor 1 scan (2 snapshots)
        comp_scan = client.post(f"/competitors/{comp1_id}/scan", headers=headers).json()
        comp_scan_id = comp_scan["id"]

    # Verify counts in DB before deletions
    assert db_session.query(Workspace).filter(Workspace.id == ws_id).count() == 1
    assert db_session.query(Competitor).filter(Competitor.workspace_id == ws_id).count() == 2
    assert db_session.query(Source).filter(Source.competitor_id.in_([comp1_id, comp2_id])).count() == 3
    assert db_session.query(ScanRun).filter(ScanRun.workspace_id == ws_id).count() == 2
    assert db_session.query(Snapshot).filter(Snapshot.scan_run_id == ws_scan_id).count() == 3
    assert db_session.query(Snapshot).filter(Snapshot.scan_run_id == comp_scan_id).count() == 2

    # Step A: Delete Competitor 2 via API
    del_comp_res = client.delete(f"/workspaces/{ws_id}/competitors/{comp2_id}", headers=headers)
    assert del_comp_res.status_code == 204

    # Verify Competitor 2 and Source 3 removed
    assert db_session.query(Competitor).filter(Competitor.id == comp2_id).count() == 0
    assert db_session.query(Source).filter(Source.id == s3).count() == 0
    # Competitor 1 and its sources remain
    assert db_session.query(Competitor).filter(Competitor.id == comp1_id).count() == 1
    assert db_session.query(Source).filter(Source.id.in_([s1, s2])).count() == 2

    # Step B: Delete ScanRun directly in DB, verify Snapshots cascade delete
    scan_to_del = db_session.query(ScanRun).filter(ScanRun.id == comp_scan_id).first()
    db_session.delete(scan_to_del)
    db_session.commit()

    assert db_session.query(ScanRun).filter(ScanRun.id == comp_scan_id).count() == 0
    assert db_session.query(Snapshot).filter(Snapshot.scan_run_id == comp_scan_id).count() == 0
    # Sources must still be intact
    assert db_session.query(Source).filter(Source.id.in_([s1, s2])).count() == 2

    # Step C: Delete entire Workspace via API
    del_ws_res = client.delete(f"/workspaces/{ws_id}", headers=headers)
    assert del_ws_res.status_code == 204

    # Verify total eradication of all child records
    assert db_session.query(Workspace).filter(Workspace.id == ws_id).count() == 0
    assert db_session.query(Competitor).filter(Competitor.workspace_id == ws_id).count() == 0
    assert db_session.query(Source).filter(Source.competitor_id == comp1_id).count() == 0
    assert db_session.query(ScanRun).filter(ScanRun.workspace_id == ws_id).count() == 0
    assert db_session.query(Snapshot).filter(Snapshot.scan_run_id == ws_scan_id).count() == 0


def test_tier4_end_to_end_user_journey_scan_workflow(client):
    """
    Tier 4 - Real-World Scenario:
    Simulate full user end-to-end operational journey:
    1. Register & authenticate user.
    2. Create market workspace.
    3. Add competitor with web + RSS feeds.
    4. Run initial full scan.
    5. Check dashboard scans list.
    6. Run targeted single-competitor scan.
    7. Inspect snapshot details and verify SHA-256 integrity and timestamps.
    """
    # 1. Register & authenticate
    headers = create_user_and_headers(client, "journey_user@example.com", name="Chief Strategist")

    # 2. Create workspace
    ws = client.post("/workspaces", json={"name": "Cybersecurity Competitive Intelligence"}, headers=headers).json()
    ws_id = ws["id"]

    # 3. Add competitor with multiple sources
    comp = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "ShieldTech Systems", "website": "https://shieldtech.io"},
        headers=headers,
    ).json()
    comp_id = comp["id"]

    src_web = client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Product Overview", "url": "https://shieldtech.io/products", "source_type": "website"},
        headers=headers,
    ).json()

    src_rss = client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Threat Intel Advisory", "url": "https://shieldtech.io/advisories.xml", "source_type": "rss"},
        headers=headers,
    ).json()

    dispatcher = E2EDispatcher()
    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=dispatcher):
        # 4. Trigger initial workspace scan
        scan1_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
        assert scan1_res.status_code == 201
        scan1 = scan1_res.json()
        assert scan1["status"] == "completed"
        assert scan1["total_sources"] == 2
        assert scan1["successful_sources"] == 2

        # 5. List scans
        scans_list = client.get(f"/workspaces/{ws_id}/scans", headers=headers).json()
        assert len(scans_list) == 1
        assert scans_list[0]["id"] == scan1["id"]

        # 6. Trigger targeted competitor scan
        scan2_res = client.post(f"/competitors/{comp_id}/scan", headers=headers)
        assert scan2_res.status_code == 201
        scan2 = scan2_res.json()
        assert scan2["competitor_id"] == comp_id

    # 7. Check source snapshot history
    web_history = client.get(f"/sources/{src_web['id']}/snapshots", headers=headers).json()
    rss_history = client.get(f"/sources/{src_rss['id']}/snapshots", headers=headers).json()

    assert len(web_history) == 2
    assert len(rss_history) == 2

    # Verify SHA-256 integrity and response times
    for s in web_history + rss_history:
        assert s["status"] == "success"
        assert len(s["content_hash"]) == 64
        assert int(s["content_hash"], 16) > 0
        assert s["response_time_ms"] is not None
        assert s["response_time_ms"] >= 0
