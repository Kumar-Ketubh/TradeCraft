# backend/tests/test_changes_api.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.models.change import Change
from app.diff.engine import DiffEngine, compute_change_hash


def create_user_and_headers(client, email="changes_user@example.com", password="password123"):
    """Register a user and return authorization header dictionary."""
    res = client.post(
        "/auth/register",
        json={"name": "Changes Tester", "email": email, "password": password},
    )
    assert res.status_code == 201, f"User registration failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_workspace_with_changes(db_session, user_email="owner@example.com"):
    """
    Directly seed DB with User, Workspace, Competitor, Sources, ScanRuns, Snapshots, and Changes.
    """
    user = db_session.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            name="Workspace Owner",
            email=user_email,
            password_hash="pbkdf2_sha256$test$hash",
        )
        db_session.add(user)
        db_session.flush()

    ws = Workspace(user_id=user.id, name="Intelligence Hub")
    db_session.add(ws)
    db_session.flush()

    comp1 = Competitor(workspace_id=ws.id, name="CloudCorp", website="https://cloudcorp.example.com")
    comp2 = Competitor(workspace_id=ws.id, name="DataScale", website="https://datascale.example.com")
    db_session.add_all([comp1, comp2])
    db_session.flush()

    src1 = Source(competitor_id=comp1.id, name="Pricing", url="https://cloudcorp.example.com/pricing", source_type="pricing")
    src2 = Source(competitor_id=comp1.id, name="Features", url="https://cloudcorp.example.com/features", source_type="website")
    src3 = Source(competitor_id=comp2.id, name="Blog", url="https://datascale.example.com/blog", source_type="blog")
    db_session.add_all([src1, src2, src3])
    db_session.flush()

    t0 = datetime.now(timezone.utc) - timedelta(hours=3)
    t1 = datetime.now(timezone.utc) - timedelta(hours=2)
    t2 = datetime.now(timezone.utc) - timedelta(hours=1)

    # Scan run 1
    scan1 = ScanRun(workspace_id=ws.id, competitor_id=comp1.id, status="completed", created_at=t0)
    # Scan run 2
    scan2 = ScanRun(workspace_id=ws.id, competitor_id=comp1.id, status="completed", created_at=t1)
    # Scan run 3
    scan3 = ScanRun(workspace_id=ws.id, competitor_id=comp2.id, status="completed", created_at=t2)
    db_session.add_all([scan1, scan2, scan3])
    db_session.flush()

    # Snapshots for src1 (Pricing)
    snap1_old = Snapshot(
        scan_run_id=scan1.id, source_id=src1.id, status="success",
        normalized_content="Starter: $29/mo\nEnterprise: $99/mo",
        content_hash="hash_old", created_at=t0,
    )
    snap1_new = Snapshot(
        scan_run_id=scan2.id, source_id=src1.id, status="success",
        normalized_content="Starter: $49/mo\nEnterprise: $149/mo",
        content_hash="hash_new", created_at=t1,
    )

    # Snapshots for src2 (Features - noise/copyright)
    snap2_old = Snapshot(
        scan_run_id=scan1.id, source_id=src2.id, status="success",
        normalized_content="CloudCorp Features\nCopyright 2024",
        content_hash="hash2_old", created_at=t0,
    )
    snap2_new = Snapshot(
        scan_run_id=scan2.id, source_id=src2.id, status="success",
        normalized_content="CloudCorp Features\nCopyright 2025",
        content_hash="hash2_new", created_at=t1,
    )

    # Snapshots for src3 (Blog)
    snap3_old = Snapshot(
        scan_run_id=scan1.id, source_id=src3.id, status="success",
        normalized_content="Latest Posts:\nArticle A",
        content_hash="hash3_old", created_at=t0,
    )
    snap3_new = Snapshot(
        scan_run_id=scan3.id, source_id=src3.id, status="success",
        normalized_content="Latest Posts:\nIntroducing Version 2.0!\nArticle A",
        content_hash="hash3_new", created_at=t2,
    )
    db_session.add_all([snap1_old, snap1_new, snap2_old, snap2_new, snap3_old, snap3_new])
    db_session.flush()

    # Change 1: Meaningful Pricing Change (scan2)
    ch1 = Change(
        workspace_id=ws.id, competitor_id=comp1.id, source_id=src1.id, scan_run_id=scan2.id,
        previous_snapshot_id=snap1_old.id, current_snapshot_id=snap1_new.id,
        change_hash=compute_change_hash("diff1"), change_type="modification",
        category="pricing_change", is_meaningful=True, significance_score=0.90,
        summary="Pricing change detected: mentions $49/mo",
        diff_unified="--- a\n+++ b\n@@ -1,2 +1,2 @@\n-Starter: $29/mo\n+Starter: $49/mo\n-Enterprise: $99/mo\n+Enterprise: $149/mo",
        diff_stats={"lines_added": 2, "lines_removed": 2},
        detected_at=t1,
    )

    # Change 2: Cosmetic Noise (scan2)
    ch2 = Change(
        workspace_id=ws.id, competitor_id=comp1.id, source_id=src2.id, scan_run_id=scan2.id,
        previous_snapshot_id=snap2_old.id, current_snapshot_id=snap2_new.id,
        change_hash=compute_change_hash("diff2"), change_type="modification",
        category="noise", is_meaningful=False, significance_score=0.0,
        summary="Copyright year roll-forward.",
        diff_unified="--- a\n+++ b\n@@ -2 +2 @@\n-Copyright 2024\n+Copyright 2025",
        diff_stats={"lines_added": 1, "lines_removed": 1},
        detected_at=t1 + timedelta(seconds=10),
    )

    # Change 3: Feature Announcement (scan3)
    ch3 = Change(
        workspace_id=ws.id, competitor_id=comp2.id, source_id=src3.id, scan_run_id=scan3.id,
        previous_snapshot_id=snap3_old.id, current_snapshot_id=snap3_new.id,
        change_hash=compute_change_hash("diff3"), change_type="addition",
        category="feature_announcement", is_meaningful=True, significance_score=0.85,
        summary="Feature announcement detected: Introducing Version 2.0!",
        diff_unified="--- a\n+++ b\n@@ -1 +1,2 @@\n Latest Posts:\n+Introducing Version 2.0!",
        diff_stats={"lines_added": 1, "lines_removed": 0},
        detected_at=t2,
    )
    db_session.add_all([ch1, ch2, ch3])
    db_session.flush()

    return {
        "user": user,
        "workspace": ws,
        "competitors": [comp1, comp2],
        "sources": [src1, src2, src3],
        "scans": [scan1, scan2, scan3],
        "changes": [ch1, ch2, ch3],
    }


def test_list_workspace_changes_default(client, db_session):
    """GET /workspaces/{id}/changes returns all detected changes ordered newest first."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    headers = create_user_and_headers(client, email=email)
    data = setup_workspace_with_changes(db_session, user_email=email)
    ws_id = data["workspace"].id

    res = client.get(f"/workspaces/{ws_id}/changes", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 3

    # Check ordering (newest detected_at first)
    assert items[0]["id"] == data["changes"][2].id  # ch3 at t2
    # Context fields populated
    assert items[0]["competitor_name"] == "DataScale"
    assert items[0]["source_name"] == "Blog"
    assert items[0]["source_url"] == "https://datascale.example.com/blog"
    # Unified diff omitted from summary list
    assert "diff_unified" not in items[0]


def test_list_workspace_changes_filtering(client, db_session):
    """Test filtering by is_meaningful, category, and competitor_id."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    headers = create_user_and_headers(client, email=email)
    data = setup_workspace_with_changes(db_session, user_email=email)
    ws_id = data["workspace"].id
    comp1_id = data["competitors"][0].id
    comp2_id = data["competitors"][1].id

    # Filter is_meaningful=true
    res_m = client.get(f"/workspaces/{ws_id}/changes?is_meaningful=true", headers=headers)
    assert res_m.status_code == 200
    m_items = res_m.json()
    assert len(m_items) == 2
    assert all(item["is_meaningful"] is True for item in m_items)

    # Filter is_meaningful=false (noise only)
    res_noise = client.get(f"/workspaces/{ws_id}/changes?is_meaningful=false", headers=headers)
    assert res_noise.status_code == 200
    noise_items = res_noise.json()
    assert len(noise_items) == 1
    assert noise_items[0]["category"] == "noise"

    # Filter category=pricing_change
    res_cat = client.get(f"/workspaces/{ws_id}/changes?category=pricing_change", headers=headers)
    assert res_cat.status_code == 200
    cat_items = res_cat.json()
    assert len(cat_items) == 1
    assert cat_items[0]["category"] == "pricing_change"

    # Filter competitor_id=comp1_id
    res_comp = client.get(f"/workspaces/{ws_id}/changes?competitor_id={comp1_id}", headers=headers)
    assert res_comp.status_code == 200
    comp_items = res_comp.json()
    assert len(comp_items) == 2
    assert all(item["competitor_id"] == comp1_id for item in comp_items)


def test_list_workspace_changes_pagination(client, db_session):
    """Test limit and offset pagination."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    headers = create_user_and_headers(client, email=email)
    data = setup_workspace_with_changes(db_session, user_email=email)
    ws_id = data["workspace"].id

    res_p1 = client.get(f"/workspaces/{ws_id}/changes?limit=2&offset=0", headers=headers)
    assert res_p1.status_code == 200
    items_p1 = res_p1.json()
    assert len(items_p1) == 2

    res_p2 = client.get(f"/workspaces/{ws_id}/changes?limit=2&offset=2", headers=headers)
    assert res_p2.status_code == 200
    items_p2 = res_p2.json()
    assert len(items_p2) == 1

    # Items do not overlap
    p1_ids = {item["id"] for item in items_p1}
    assert items_p2[0]["id"] not in p1_ids


def test_get_change_detail_returns_diff(client, db_session):
    """GET /changes/{id} returns ChangeDetailResponse with full unified diff."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    headers = create_user_and_headers(client, email=email)
    data = setup_workspace_with_changes(db_session, user_email=email)
    ch1 = data["changes"][0]

    res = client.get(f"/changes/{ch1.id}", headers=headers)
    assert res.status_code == 200
    detail = res.json()

    assert detail["id"] == ch1.id
    assert detail["workspace_id"] == data["workspace"].id
    assert detail["competitor_name"] == "CloudCorp"
    assert detail["source_name"] == "Pricing"
    assert detail["category"] == "pricing_change"
    assert detail["is_meaningful"] is True
    assert "diff_unified" in detail
    assert "-Starter: $29/mo" in detail["diff_unified"]
    assert "+Starter: $49/mo" in detail["diff_unified"]


def test_get_scan_changes(client, db_session):
    """GET /scans/{id}/changes returns changes produced during a specific scan run."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    headers = create_user_and_headers(client, email=email)
    data = setup_workspace_with_changes(db_session, user_email=email)
    scan2_id = data["scans"][1].id
    scan1_id = data["scans"][0].id

    # Scan 2 produced 2 changes (ch1, ch2)
    res_s2 = client.get(f"/scans/{scan2_id}/changes", headers=headers)
    assert res_s2.status_code == 200
    changes_s2 = res_s2.json()
    assert len(changes_s2) == 2

    # Scan 1 was baseline, produced 0 changes
    res_s1 = client.get(f"/scans/{scan1_id}/changes", headers=headers)
    assert res_s1.status_code == 200
    changes_s1 = res_s1.json()
    assert len(changes_s1) == 0


def test_multi_tenant_isolation_returns_404_and_401(client, db_session):
    """Ensure cross-tenant access returns 404 and unauthenticated calls return 401."""
    # User A setup
    email_a = f"user_a_{uuid.uuid4().hex[:8]}@example.com"
    headers_a = create_user_and_headers(client, email=email_a)
    data_a = setup_workspace_with_changes(db_session, user_email=email_a)
    ws_a_id = data_a["workspace"].id
    change_a_id = data_a["changes"][0].id
    scan_a_id = data_a["scans"][1].id

    # User B setup
    email_b = f"user_b_{uuid.uuid4().hex[:8]}@example.com"
    headers_b = create_user_and_headers(client, email=email_b)

    # 1. User B attempts to access User A's workspace changes -> 404
    res_ws = client.get(f"/workspaces/{ws_a_id}/changes", headers=headers_b)
    assert res_ws.status_code == 404

    # 2. User B attempts to access User A's change detail -> 404
    res_ch = client.get(f"/changes/{change_a_id}", headers=headers_b)
    assert res_ch.status_code == 404

    # 3. User B attempts to access User A's scan changes -> 404
    res_sc = client.get(f"/scans/{scan_a_id}/changes", headers=headers_b)
    assert res_sc.status_code == 404

    # 4. User A passes unowned competitor ID to workspace changes -> 404
    fake_comp_id = str(uuid.uuid4())
    res_bad_comp = client.get(f"/workspaces/{ws_a_id}/changes?competitor_id={fake_comp_id}", headers=headers_a)
    assert res_bad_comp.status_code == 404

    # 5. Unauthenticated calls -> 401
    assert client.get(f"/workspaces/{ws_a_id}/changes").status_code == 401
    assert client.get(f"/changes/{change_a_id}").status_code == 401
    assert client.get(f"/scans/{scan_a_id}/changes").status_code == 401


def test_end_to_end_scan_detection_via_api(client):
    """End-to-end integration: running a scan via API on modified source detects change."""
    headers = create_user_and_headers(client, email="e2e_api@example.com")
    ws = client.post("/workspaces", json={"name": "Live Scanner WS"}, headers=headers).json()
    comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "SaaS Acme"}, headers=headers).json()
    
    url = "https://saas-acme.example.com/pricing"
    src = client.post(
        f"/competitors/{comp['id']}/sources",
        json={"name": "Pricing Page", "url": url, "source_type": "website"},
        headers=headers,
    ).json()

    # Baseline scan mock response
    v1_html = "<html><body><h1>Pricing</h1><p>Pro Plan: $49/mo</p></body></html>"
    v2_html = "<html><body><h1>Pricing</h1><p>Pro Plan: $79/mo (New Features)</p></body></html>"

    with patch("httpx.AsyncClient.get") as mock_get:
        # Scan 1: Baseline
        mock_resp1 = AsyncMock()
        mock_resp1.status_code = 200
        mock_resp1.text = v1_html
        mock_resp1.headers = {"content-type": "text/html"}
        mock_get.return_value = mock_resp1

        s1_res = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)
        assert s1_res.status_code == 201
        s1 = s1_res.json()

        # Check that baseline scan produces zero changes
        changes_s1 = client.get(f"/scans/{s1['id']}/changes", headers=headers).json()
        assert len(changes_s1) == 0

        # Scan 2: Content Updated
        mock_resp2 = AsyncMock()
        mock_resp2.status_code = 200
        mock_resp2.text = v2_html
        mock_resp2.headers = {"content-type": "text/html"}
        mock_get.return_value = mock_resp2

        s2_res = client.post(f"/workspaces/{ws['id']}/scan", headers=headers)
        assert s2_res.status_code == 201
        s2 = s2_res.json()

        # Check that scan 2 automatically detected and persisted 1 change
        changes_s2 = client.get(f"/scans/{s2['id']}/changes", headers=headers).json()
        assert len(changes_s2) == 1
        ch = changes_s2[0]
        assert ch["category"] == "pricing_change"
        assert ch["is_meaningful"] is True

        # Query workspace changes
        ws_changes = client.get(f"/workspaces/{ws['id']}/changes", headers=headers).json()
        assert len(ws_changes) == 1
        assert ws_changes[0]["id"] == ch["id"]

        # Query full detail
        detail = client.get(f"/changes/{ch['id']}", headers=headers).json()
        assert "-Pro Plan: $49/mo" in detail["diff_unified"]
        assert "+Pro Plan: $79/mo (New Features)" in detail["diff_unified"]
