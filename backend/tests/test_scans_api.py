# backend/tests/test_scans_api.py
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.services.scan_service import ScanService, scan_workspace, scan_competitor


def create_user_and_headers(client, email="scanner_user@example.com", password="password123"):
    """Helper to register user and obtain auth headers."""
    res = client.post(
        "/auth/register",
        json={"name": "Scanner User", "email": email, "password": password},
    ).json()
    return {"Authorization": f"Bearer {res['access_token']}"}


def setup_workspace_with_sources(client, headers, ws_name="Market Intelligence"):
    """Helper to create workspace, competitor, and sources."""
    ws = client.post("/workspaces", json={"name": ws_name}, headers=headers).json()
    ws_id = ws["id"]

    comp = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Apex Rival", "website": "https://apex.example.com"},
        headers=headers,
    ).json()
    comp_id = comp["id"]

    src1 = client.post(
        f"/competitors/{comp_id}/sources",
        json={
            "name": "Landing Page",
            "url": "https://apex.example.com",
            "source_type": "website",
            "monitoring_enabled": True,
        },
        headers=headers,
    ).json()

    src2 = client.post(
        f"/competitors/{comp_id}/sources",
        json={
            "name": "Product News RSS",
            "url": "https://apex.example.com/feed.xml",
            "source_type": "rss",
            "monitoring_enabled": True,
        },
        headers=headers,
    ).json()

    return ws_id, comp_id, [src1["id"], src2["id"]]


def mock_http_response_dispatcher(url, *args, **kwargs):
    """Dispatcher returning realistic HTTP responses or raising network errors."""
    url_str = str(url)
    if "404" in url_str:
        return httpx.Response(404, text="Not Found", request=httpx.Request("GET", url_str))
    elif "500" in url_str:
        return httpx.Response(500, text="Internal Server Error", request=httpx.Request("GET", url_str))
    elif "timeout" in url_str:
        raise httpx.ReadTimeout("Request timed out", request=httpx.Request("GET", url_str))
    elif "rss" in url_str or "feed" in url_str or url_str.endswith(".xml"):
        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Apex Updates</title>
                <link>https://apex.example.com</link>
                <item>
                    <title>Version 3.0 Released</title>
                    <link>https://apex.example.com/blog/v3</link>
                    <description>Brand new real-time intelligence feeds.</description>
                </item>
            </channel>
        </rss>"""
        return httpx.Response(200, text=rss_content, request=httpx.Request("GET", url_str))
    else:
        html_content = """<!DOCTYPE html>
        <html>
            <head><title>Apex Rival - Solutions</title></head>
            <body>
                <h1>Competitive Offerings</h1>
                <p>Enterprise data intelligence platform with high accuracy.</p>
            </body>
        </html>"""
        return httpx.Response(200, text=html_content, request=httpx.Request("GET", url_str))


# ============================================================================
# 1. Workspace Scan API Tests
# ============================================================================

def test_workspace_scan_initiates_and_persists_snapshots(client):
    headers = create_user_and_headers(client, "ws_scan_user@example.com")
    ws_id, comp_id, source_ids = setup_workspace_with_sources(client, headers)

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan_data = scan_res.json()
    assert scan_data["workspace_id"] == ws_id
    assert scan_data["competitor_id"] is None
    assert scan_data["status"] == "completed"
    assert scan_data["total_sources"] == 2
    assert scan_data["successful_sources"] == 2
    assert scan_data["failed_sources"] == 0
    assert "scan_run_id" in scan_data
    assert scan_data["scan_run_id"] == scan_data["id"]

    # Check scan detail endpoint
    scan_id = scan_data["id"]
    detail_res = client.get(f"/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert len(detail_data["snapshots"]) == 2
    for snap in detail_data["snapshots"]:
        assert snap["scan_run_id"] == scan_id
        assert snap["status"] == "success"
        assert snap["status_code"] == 200
        assert snap["content_hash"] is not None
        assert len(snap["content_hash"]) == 64
        assert snap["normalized_content"] is not None


def test_workspace_scan_zero_active_sources(client):
    headers = create_user_and_headers(client, "empty_ws@example.com")
    ws = client.post("/workspaces", json={"name": "Empty Workspace"}, headers=headers).json()
    ws_id = ws["id"]

    scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
    assert scan_res.status_code == 201
    data = scan_res.json()
    assert data["workspace_id"] == ws_id
    assert data["total_sources"] == 0
    assert data["successful_sources"] == 0
    assert data["failed_sources"] == 0
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


# ============================================================================
# 2. Competitor Scan API Tests
# ============================================================================

def test_competitor_scan_initiates_for_single_competitor(client):
    headers = create_user_and_headers(client, "comp_scan@example.com")
    ws = client.post("/workspaces", json={"name": "Multi-Comp Workspace"}, headers=headers).json()
    ws_id = ws["id"]

    comp1 = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Comp 1"}, headers=headers).json()
    comp2 = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Comp 2"}, headers=headers).json()

    # Comp 1 has 2 sources
    client.post(
        f"/competitors/{comp1['id']}/sources",
        json={"name": "Comp 1 Web", "url": "https://comp1.com", "source_type": "website"},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp1['id']}/sources",
        json={"name": "Comp 1 Blog", "url": "https://comp1.com/feed.xml", "source_type": "rss"},
        headers=headers,
    )
    # Comp 2 has 1 source
    client.post(
        f"/competitors/{comp2['id']}/sources",
        json={"name": "Comp 2 Web", "url": "https://comp2.com", "source_type": "website"},
        headers=headers,
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_res = client.post(f"/competitors/{comp1['id']}/scan", headers=headers)

    assert scan_res.status_code == 201
    data = scan_res.json()
    assert data["workspace_id"] == ws_id
    assert data["competitor_id"] == comp1["id"]
    assert data["total_sources"] == 2
    assert data["successful_sources"] == 2
    assert data["status"] == "completed"


def test_competitor_scan_zero_sources(client):
    headers = create_user_and_headers(client, "empty_comp@example.com")
    ws = client.post("/workspaces", json={"name": "Comp Zero WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Empty Comp"}, headers=headers).json()

    scan_res = client.post(f"/competitors/{comp['id']}/scan", headers=headers)
    assert scan_res.status_code == 201
    data = scan_res.json()
    assert data["competitor_id"] == comp["id"]
    assert data["total_sources"] == 0
    assert data["status"] == "completed"


# ============================================================================
# 3. List Scans & Detail Endpoints Tests
# ============================================================================

def test_list_workspace_scans_returns_history(client):
    headers = create_user_and_headers(client, "history_user@example.com")
    ws_id, comp_id, _ = setup_workspace_with_sources(client, headers, "History WS")

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        client.post(f"/workspaces/{ws_id}/scan", headers=headers)
        client.post(f"/competitors/{comp_id}/scan", headers=headers)

    list_res = client.get(f"/workspaces/{ws_id}/scans", headers=headers)
    assert list_res.status_code == 200
    scans = list_res.json()
    assert len(scans) == 2
    # Verify ordered newest first
    assert scans[0]["created_at"] >= scans[1]["created_at"]


def test_get_scan_detail_returns_snapshots(client):
    headers = create_user_and_headers(client, "detail_user@example.com")
    ws_id, comp_id, _ = setup_workspace_with_sources(client, headers, "Detail WS")

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    scan_id = scan_res.json()["id"]
    detail_res = client.get(f"/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == scan_id
    assert "snapshots" in data
    assert len(data["snapshots"]) == 2


# ============================================================================
# 4. Source Snapshots Endpoint Tests
# ============================================================================

def test_get_source_snapshots_returns_history(client):
    headers = create_user_and_headers(client, "source_snap_user@example.com")
    ws_id, comp_id, source_ids = setup_workspace_with_sources(client, headers, "Snap History WS")
    target_source_id = source_ids[0]

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        # Trigger scan twice
        client.post(f"/workspaces/{ws_id}/scan", headers=headers)
        client.post(f"/competitors/{comp_id}/scan", headers=headers)

    res = client.get(f"/sources/{target_source_id}/snapshots", headers=headers)
    assert res.status_code == 200
    snapshots = res.json()
    assert len(snapshots) == 2
    for snap in snapshots:
        assert snap["source_id"] == target_source_id
        assert snap["status"] == "success"
        assert snap["status_code"] == 200


# ============================================================================
# 5. Fault Tolerance & Error Handling Tests
# ============================================================================

def test_fault_tolerance_batch_scan_with_mixed_outcomes(client):
    """
    Simulate batch scan where individual sources yield 200, 404, 500, and timeout.
    The scan must not crash, must record snapshot for each, and mark scan as partial.
    """
    headers = create_user_and_headers(client, "fault_user@example.com")
    ws = client.post("/workspaces", json={"name": "Fault Tolerance WS"}, headers=headers).json()
    ws_id = ws["id"]
    comp = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Fragile Corp"}, headers=headers).json()
    comp_id = comp["id"]

    # 4 distinct sources
    s_good = client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Good Site", "url": "https://fragile.com/ok", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s_404 = client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Dead Page", "url": "https://fragile.com/404", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s_500 = client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Crashing API", "url": "https://fragile.com/500", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    s_timeout = client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Slow Site", "url": "https://fragile.com/timeout", "source_type": "website"},
        headers=headers,
    ).json()["id"]

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan = scan_res.json()
    assert scan["status"] == "partial"
    assert scan["total_sources"] == 4
    assert scan["successful_sources"] == 1
    assert scan["failed_sources"] == 3
    assert "3 of 4 sources failed to fetch" in scan["error_message"]

    # Verify all 4 snapshots persisted
    scan_id = scan["id"]
    detail = client.get(f"/scans/{scan_id}", headers=headers).json()
    snapshots = detail["snapshots"]
    assert len(snapshots) == 4

    snap_by_src = {s["source_id"]: s for s in snapshots}
    assert snap_by_src[s_good]["status"] == "success"
    assert snap_by_src[s_good]["status_code"] == 200

    assert snap_by_src[s_404]["status"] == "error"
    assert snap_by_src[s_404]["status_code"] == 404
    assert "404" in snap_by_src[s_404]["error_message"]

    assert snap_by_src[s_500]["status"] == "error"
    assert snap_by_src[s_500]["status_code"] == 500
    assert "500" in snap_by_src[s_500]["error_message"]

    assert snap_by_src[s_timeout]["status"] == "error"
    assert snap_by_src[s_timeout]["status_code"] is None
    assert "timed out" in snap_by_src[s_timeout]["error_message"].lower()


def test_fault_tolerance_all_sources_failed(client):
    """When all sources fail, scan status must be 'failed'."""
    headers = create_user_and_headers(client, "all_fail@example.com")
    ws = client.post("/workspaces", json={"name": "All Fail WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Broken Corp"}, headers=headers).json()

    client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Fail 1", "url": "https://broken.com/500", "source_type": "website"},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Fail 2", "url": "https://broken.com/404", "source_type": "website"},
        headers=headers,
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_res = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan = scan_res.json()
    assert scan["status"] == "failed"
    assert scan["successful_sources"] == 0
    assert scan["failed_sources"] == 2
    assert "All 2 sources failed" in scan["error_message"]


# ============================================================================
# 6. Monitoring Disabled Filtering Tests
# ============================================================================

def test_disabled_monitoring_sources_and_competitors_are_skipped(client):
    headers = create_user_and_headers(client, "filter_user@example.com")
    ws = client.post("/workspaces", json={"name": "Filter WS"}, headers=headers).json()
    ws_id = ws["id"]

    # Active competitor with 1 active source and 1 disabled source
    comp_active = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Active Comp", "monitoring_enabled": True},
        headers=headers,
    ).json()
    client.post(
        f"/competitors/{comp_active['id']}/sources",
        json={"name": "Enabled Source", "url": "https://active.com/1", "monitoring_enabled": True},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp_active['id']}/sources",
        json={"name": "Disabled Source", "url": "https://active.com/2", "monitoring_enabled": False},
        headers=headers,
    )

    # Disabled competitor with 1 active source
    comp_disabled = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "Disabled Comp"},
        headers=headers,
    ).json()
    # Update competitor to monitoring_enabled = False
    client.put(
        f"/workspaces/{ws_id}/competitors/{comp_disabled['id']}",
        json={"monitoring_enabled": False},
        headers=headers,
    )
    client.post(
        f"/competitors/{comp_disabled['id']}/sources",
        json={"name": "Source on disabled comp", "url": "https://disabled.com/1", "monitoring_enabled": True},
        headers=headers,
    )

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

    assert scan_res.status_code == 201
    scan = scan_res.json()
    # Only 1 source should have been scanned
    assert scan["total_sources"] == 1
    assert scan["successful_sources"] == 1


# ============================================================================
# 7. Multi-Tenant Isolation Tests (404 on Cross-Tenant Access)
# ============================================================================

def test_multi_tenant_isolation_cross_tenant_access_returns_404(client):
    headers1 = create_user_and_headers(client, "owner@example.com")
    headers2 = create_user_and_headers(client, "intruder@example.com")

    ws1_id, comp1_id, source1_ids = setup_workspace_with_sources(client, headers1, "Owner WS")
    src1_id = source1_ids[0]

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_res = client.post(f"/workspaces/{ws1_id}/scan", headers=headers1)
    scan1_id = scan_res.json()["id"]

    # 1. User 2 triggers scan on User 1's workspace -> 404
    res = client.post(f"/workspaces/{ws1_id}/scan", headers=headers2)
    assert res.status_code == 404
    assert "Workspace not found" in res.json()["detail"]

    # 2. User 2 triggers scan on User 1's competitor -> 404
    res = client.post(f"/competitors/{comp1_id}/scan", headers=headers2)
    assert res.status_code == 404
    assert "Competitor not found" in res.json()["detail"]

    # 3. User 2 lists scans for User 1's workspace -> 404
    res = client.get(f"/workspaces/{ws1_id}/scans", headers=headers2)
    assert res.status_code == 404
    assert "Workspace not found" in res.json()["detail"]

    # 4. User 2 queries User 1's scan detail -> 404
    res = client.get(f"/scans/{scan1_id}", headers=headers2)
    assert res.status_code == 404
    assert "Scan run not found" in res.json()["detail"]

    # 5. User 2 queries snapshots for User 1's source -> 404
    res = client.get(f"/sources/{src1_id}/snapshots", headers=headers2)
    assert res.status_code == 404
    assert "Source not found" in res.json()["detail"]


# ============================================================================
# 8. Unauthenticated Access Tests (401 Unauthorized)
# ============================================================================

def test_unauthenticated_requests_receive_401(client):
    fake_id = "00000000-0000-0000-0000-000000000000"

    # All 5 endpoints without Authorization header must return 401
    assert client.post(f"/workspaces/{fake_id}/scan").status_code == 401
    assert client.post(f"/competitors/{fake_id}/scan").status_code == 401
    assert client.get(f"/workspaces/{fake_id}/scans").status_code == 401
    assert client.get(f"/scans/{fake_id}").status_code == 401
    assert client.get(f"/sources/{fake_id}/snapshots").status_code == 401

    # Endpoints with invalid Bearer token must return 401
    bad_headers = {"Authorization": "Bearer invalid.token.payload"}
    assert client.post(f"/workspaces/{fake_id}/scan", headers=bad_headers).status_code == 401
    assert client.post(f"/competitors/{fake_id}/scan", headers=bad_headers).status_code == 401
    assert client.get(f"/workspaces/{fake_id}/scans", headers=bad_headers).status_code == 401
    assert client.get(f"/scans/{fake_id}", headers=bad_headers).status_code == 401
    assert client.get(f"/sources/{fake_id}/snapshots", headers=bad_headers).status_code == 401


# ============================================================================
# 9. Direct ScanService Unit Tests
# ============================================================================

@pytest.mark.anyio
async def test_scan_service_direct_execution(db_session):
    from app.models.user import User
    from app.core.security import get_password_hash

    # Create user, workspace, competitor, sources directly in DB
    user = User(name="Direct User", email="direct@example.com", password_hash=get_password_hash("pass"))
    db_session.add(user)
    db_session.commit()

    ws = Workspace(name="Direct WS", user_id=user.id)
    db_session.add(ws)
    db_session.commit()

    comp = Competitor(name="Direct Comp", workspace_id=ws.id, monitoring_enabled=True)
    db_session.add(comp)
    db_session.commit()

    src1 = Source(name="S1", url="https://direct.com/page", competitor_id=comp.id, monitoring_enabled=True)
    src2 = Source(name="S2", url="https://direct.com/feed.xml", competitor_id=comp.id, monitoring_enabled=True)
    db_session.add_all([src1, src2])
    db_session.commit()

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_http_response_dispatcher):
        scan_run = await scan_workspace(ws.id, db=db_session)

    assert scan_run.status == "completed"
    assert scan_run.total_sources == 2
    assert scan_run.successful_sources == 2
    assert scan_run.failed_sources == 0
    assert len(scan_run.snapshots) == 2
