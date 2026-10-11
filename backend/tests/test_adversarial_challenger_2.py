# backend/tests/test_adversarial_challenger_2.py
"""
Adversarial Verification Suite - Challenger 2
=============================================
Focus Areas:
1. Multi-Tenant Penetration & Cross-Tenant Tampering (Strict HTTP 404 Invariance)
2. Unauthenticated & Tampered Token Handling (Strict HTTP 401 Invariance)
3. Empty & Boundary Input Fuzzing (Path traversal, SQLi/XSS strings, extreme lengths, empty hierarchies)
4. Data Integrity & Immutability (SHA-256 64-hex validity, immutable historical snapshots)
"""

import re
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
import httpx
import jwt
import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.adapters.hashing import compute_content_hash


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def create_user_and_headers(client, email: str, name: str = "Test User"):
    """Helper to register user and obtain bearer authorization header."""
    res = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "SecurePassword123!"},
    )
    assert res.status_code == 201, f"Failed to register {email}: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_tenant_hierarchy(client, headers, prefix="Tenant"):
    """Creates a full workspace -> competitor -> 2 sources hierarchy for a tenant."""
    ws = client.post(
        "/workspaces",
        json={"name": f"{prefix} Workspace"},
        headers=headers,
    ).json()
    ws_id = ws["id"]

    comp = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": f"{prefix} Competitor", "website": f"https://{prefix.lower()}.example.com"},
        headers=headers,
    ).json()
    comp_id = comp["id"]

    src1 = client.post(
        f"/competitors/{comp_id}/sources",
        json={
            "name": f"{prefix} Website",
            "url": f"https://{prefix.lower()}.example.com/home",
            "source_type": "website",
            "monitoring_enabled": True,
        },
        headers=headers,
    ).json()

    src2 = client.post(
        f"/competitors/{comp_id}/sources",
        json={
            "name": f"{prefix} RSS Feed",
            "url": f"https://{prefix.lower()}.example.com/rss.xml",
            "source_type": "rss",
            "monitoring_enabled": True,
        },
        headers=headers,
    ).json()

    return ws_id, comp_id, [src1["id"], src2["id"]]


def mock_dispatcher(url, *args, **kwargs):
    """Mock dispatcher for adversarial test executions."""
    url_str = str(url)
    if "404" in url_str:
        return httpx.Response(404, text="Not Found", request=httpx.Request("GET", url_str))
    elif "500" in url_str:
        return httpx.Response(500, text="Internal Error", request=httpx.Request("GET", url_str))
    elif "timeout" in url_str:
        raise httpx.ReadTimeout("Timeout reached", request=httpx.Request("GET", url_str))
    elif "rss" in url_str:
        xml = """<?xml version="1.0"?><rss version="2.0"><channel><title>News</title><item><title>Item 1</title><link>https://item1.com</link></item></channel></rss>"""
        return httpx.Response(200, text=xml, request=httpx.Request("GET", url_str))
    else:
        html = "<html><body><h1>Adversarial Test Target</h1><p>Clean payload data.</p></body></html>"
        return httpx.Response(200, text=html, request=httpx.Request("GET", url_str))


# ===========================================================================
# 1. Multi-Tenant Penetration & Cross-Tenant Tampering
# ===========================================================================

class TestMultiTenantPenetration:
    """
    Adversarial verification of multi-tenant isolation across all 5 REST scan endpoints.
    Every cross-tenant operation must return HTTP 404 without data leakage.
    """

    def test_cross_tenant_workspace_scan_trigger_rejected(self, client):
        headers_a = create_user_and_headers(client, "victim_a@tenant.com", "Victim A")
        headers_b = create_user_and_headers(client, "attacker_b@tenant.com", "Attacker B")

        ws_a_id, _, _ = setup_tenant_hierarchy(client, headers_a, "Victim A")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            res = client.post(f"/workspaces/{ws_a_id}/scan", headers=headers_b)

        assert res.status_code == 404
        data = res.json()
        assert "not found" in data["detail"].lower()

    def test_cross_tenant_workspace_scans_list_rejected(self, client):
        headers_a = create_user_and_headers(client, "victim_a2@tenant.com", "Victim A2")
        headers_b = create_user_and_headers(client, "attacker_b2@tenant.com", "Attacker B2")

        ws_a_id, _, _ = setup_tenant_hierarchy(client, headers_a, "Victim A2")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            client.post(f"/workspaces/{ws_a_id}/scan", headers=headers_a)

        res = client.get(f"/workspaces/{ws_a_id}/scans", headers=headers_b)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_cross_tenant_competitor_scan_trigger_rejected(self, client):
        headers_a = create_user_and_headers(client, "victim_a3@tenant.com", "Victim A3")
        headers_b = create_user_and_headers(client, "attacker_b3@tenant.com", "Attacker B3")

        _, comp_a_id, _ = setup_tenant_hierarchy(client, headers_a, "Victim A3")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            res = client.post(f"/competitors/{comp_a_id}/scan", headers=headers_b)

        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_cross_tenant_scan_detail_lookup_rejected(self, client):
        headers_a = create_user_and_headers(client, "victim_a4@tenant.com", "Victim A4")
        headers_b = create_user_and_headers(client, "attacker_b4@tenant.com", "Attacker B4")

        ws_a_id, _, _ = setup_tenant_hierarchy(client, headers_a, "Victim A4")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            scan_run = client.post(f"/workspaces/{ws_a_id}/scan", headers=headers_a).json()

        scan_id = scan_run["id"]

        # Attacker B attempts to view Victim A's scan details
        res = client.get(f"/scans/{scan_id}", headers=headers_b)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_cross_tenant_source_snapshots_history_rejected(self, client):
        headers_a = create_user_and_headers(client, "victim_a5@tenant.com", "Victim A5")
        headers_b = create_user_and_headers(client, "attacker_b5@tenant.com", "Attacker B5")

        ws_a_id, _, source_a_ids = setup_tenant_hierarchy(client, headers_a, "Victim A5")
        src_a_id = source_a_ids[0]

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            client.post(f"/workspaces/{ws_a_id}/scan", headers=headers_a)

        # Attacker B attempts to view snapshots for Victim A's source
        res = client.get(f"/sources/{src_a_id}/snapshots", headers=headers_b)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_zero_knowledge_existence_oracle_invariance(self, client):
        """
        Verify that foreign existing resource vs non-existent UUID return identical
        HTTP status 404, preventing resource enumeration/existence side-channels.
        """
        headers_a = create_user_and_headers(client, "victim_zk@tenant.com", "Victim ZK")
        headers_b = create_user_and_headers(client, "probe_zk@tenant.com", "Probe ZK")

        ws_a_id, comp_a_id, src_a_ids = setup_tenant_hierarchy(client, headers_a, "Victim ZK")
        fake_uuid = "00000000-0000-0000-0000-000000000000"

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            scan_a = client.post(f"/workspaces/{ws_a_id}/scan", headers=headers_a).json()

        scan_a_id = scan_a["id"]
        src_a_id = src_a_ids[0]

        # Workspace scan
        res_real = client.post(f"/workspaces/{ws_a_id}/scan", headers=headers_b)
        res_fake = client.post(f"/workspaces/{fake_uuid}/scan", headers=headers_b)
        assert res_real.status_code == res_fake.status_code == 404

        # Competitor scan
        res_real = client.post(f"/competitors/{comp_a_id}/scan", headers=headers_b)
        res_fake = client.post(f"/competitors/{fake_uuid}/scan", headers=headers_b)
        assert res_real.status_code == res_fake.status_code == 404

        # Workspace scans list
        res_real = client.get(f"/workspaces/{ws_a_id}/scans", headers=headers_b)
        res_fake = client.get(f"/workspaces/{fake_uuid}/scans", headers=headers_b)
        assert res_real.status_code == res_fake.status_code == 404

        # Scan detail
        res_real = client.get(f"/scans/{scan_a_id}", headers=headers_b)
        res_fake = client.get(f"/scans/{fake_uuid}", headers=headers_b)
        assert res_real.status_code == res_fake.status_code == 404

        # Source snapshots
        res_real = client.get(f"/sources/{src_a_id}/snapshots", headers=headers_b)
        res_fake = client.get(f"/sources/{fake_uuid}/snapshots", headers=headers_b)
        assert res_real.status_code == res_fake.status_code == 404


# ===========================================================================
# 2. Unauthenticated & Tampered Token Handling
# ===========================================================================

class TestTokenSecurityAndTampering:
    """
    Adversarial verification of authentication invariants.
    Missing tokens, expired tokens, forged signatures, and nonexistent user IDs
    must strictly return HTTP 401.
    """

    @pytest.fixture(autouse=True)
    def setup_target(self, client):
        headers = create_user_and_headers(client, "auth_target@tenant.com")
        ws_id, comp_id, src_ids = setup_tenant_hierarchy(client, headers, "AuthTarget")
        self.ws_id = ws_id
        self.comp_id = comp_id
        self.src_id = src_ids[0]
        self.headers = headers

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            scan = client.post(f"/workspaces/{ws_id}/scan", headers=headers).json()
        self.scan_id = scan["id"]

    def _assert_all_endpoints_return_401(self, client, auth_headers):
        endpoints = [
            ("POST", f"/workspaces/{self.ws_id}/scan"),
            ("POST", f"/competitors/{self.comp_id}/scan"),
            ("GET", f"/workspaces/{self.ws_id}/scans"),
            ("GET", f"/scans/{self.scan_id}"),
            ("GET", f"/sources/{self.src_id}/snapshots"),
        ]
        for method, path in endpoints:
            if method == "POST":
                res = client.post(path, headers=auth_headers)
            else:
                res = client.get(path, headers=auth_headers)
            assert res.status_code == 401, f"{method} {path} with headers {auth_headers} returned {res.status_code}: {res.text}"

    def test_missing_authorization_header(self, client):
        self._assert_all_endpoints_return_401(client, {})

    def test_empty_bearer_token(self, client):
        self._assert_all_endpoints_return_401(client, {"Authorization": "Bearer "})

    def test_malformed_token_string(self, client):
        self._assert_all_endpoints_return_401(client, {"Authorization": "Bearer not-a-jwt-token"})
        self._assert_all_endpoints_return_401(client, {"Authorization": "Bearer abc.def"})

    def test_expired_jwt_token(self, client):
        expired_payload = {
            "sub": "some-user-id",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        self._assert_all_endpoints_return_401(client, {"Authorization": f"Bearer {expired_token}"})

    def test_tampered_jwt_signature(self, client):
        valid_payload = {
            "sub": "some-user-id",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        valid_token = jwt.encode(valid_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        # Flip the last 4 characters of the signature
        tampered_token = valid_token[:-4] + "xxxx"
        self._assert_all_endpoints_return_401(client, {"Authorization": f"Bearer {tampered_token}"})

    def test_jwt_signed_with_wrong_secret(self, client):
        alien_payload = {
            "sub": "some-user-id",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        alien_token = jwt.encode(alien_payload, "completely-wrong-secret-key-123", algorithm=settings.JWT_ALGORITHM)
        self._assert_all_endpoints_return_401(client, {"Authorization": f"Bearer {alien_token}"})

    def test_jwt_with_nonexistent_user_id(self, client):
        ghost_payload = {
            "sub": "00000000-0000-0000-0000-ffffffffffff",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        ghost_token = jwt.encode(ghost_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        self._assert_all_endpoints_return_401(client, {"Authorization": f"Bearer {ghost_token}"})

    def test_jwt_with_empty_or_null_subject(self, client):
        null_sub_payload = {
            "sub": None,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        null_token = jwt.encode(null_sub_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        self._assert_all_endpoints_return_401(client, {"Authorization": f"Bearer {null_token}"})


# ===========================================================================
# 3. Empty & Boundary Input Fuzzing
# ===========================================================================

class TestBoundaryAndInputFuzzing:
    """
    Boundary conditions, SQL injection patterns, path traversal,
    and degenerate workspace structures.
    """

    def test_path_traversal_and_sqli_patterns_in_ids(self, client):
        headers = create_user_and_headers(client, "fuzz_user@tenant.com")
        fuzz_vectors = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "' OR '1'='1",
            "\" OR \"1\"=\"1",
            "; DROP TABLE scan_runs; --",
            "<script>alert(1)</script>",
            "null",
            "undefined",
            " " * 50,
            "A" * 1024,
            "%00",
        ]

        for vector in fuzz_vectors:
            # Workspace scan
            res = client.post(f"/workspaces/{vector}/scan", headers=headers)
            assert res.status_code in (404, 422), f"Vector {vector!r} on workspace scan gave {res.status_code}"

            # Competitor scan
            res = client.post(f"/competitors/{vector}/scan", headers=headers)
            assert res.status_code in (404, 422), f"Vector {vector!r} on competitor scan gave {res.status_code}"

            # Workspace scans list
            res = client.get(f"/workspaces/{vector}/scans", headers=headers)
            assert res.status_code in (404, 422), f"Vector {vector!r} on workspace scans list gave {res.status_code}"

            # Scan detail
            res = client.get(f"/scans/{vector}", headers=headers)
            assert res.status_code in (404, 422), f"Vector {vector!r} on scan detail gave {res.status_code}"

            # Source snapshots
            res = client.get(f"/sources/{vector}/snapshots", headers=headers)
            assert res.status_code in (404, 422), f"Vector {vector!r} on source snapshots gave {res.status_code}"

    def test_workspace_scan_with_all_monitoring_disabled(self, client):
        headers = create_user_and_headers(client, "disabled_all@tenant.com")
        ws = client.post("/workspaces", json={"name": "All Disabled WS"}, headers=headers).json()
        ws_id = ws["id"]

        comp = client.post(f"/workspaces/{ws_id}/competitors", json={"name": "Comp A"}, headers=headers).json()
        comp_id = comp["id"]

        # Disable competitor
        client.put(f"/workspaces/{ws_id}/competitors/{comp_id}", json={"monitoring_enabled": False}, headers=headers)

        # Add disabled source
        client.post(
            f"/competitors/{comp_id}/sources",
            json={"name": "Disabled Src", "url": "https://example.com", "monitoring_enabled": False},
            headers=headers,
        )

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            res = client.post(f"/workspaces/{ws_id}/scan", headers=headers)

        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "completed"
        assert data["total_sources"] == 0
        assert data["successful_sources"] == 0
        assert data["failed_sources"] == 0
        assert data["completed_at"] is not None

    def test_competitor_scan_with_disabled_sources_only(self, client):
        headers = create_user_and_headers(client, "disabled_src_only@tenant.com")
        ws = client.post("/workspaces", json={"name": "WS"}, headers=headers).json()
        comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Comp"}, headers=headers).json()

        # Add source with monitoring_enabled=False
        client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "Disabled Source", "url": "https://example.com/disabled", "monitoring_enabled": False},
            headers=headers,
        )

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            res = client.post(f"/competitors/{comp['id']}/scan", headers=headers)

        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "completed"
        assert data["total_sources"] == 0
        assert data["successful_sources"] == 0
        assert data["failed_sources"] == 0

    def test_cascade_deleted_scan_run_lookup_returns_404(self, client):
        headers = create_user_and_headers(client, "cascade_fuzz@tenant.com")
        ws_id, comp_id, _ = setup_tenant_hierarchy(client, headers, "CascadeFuzz")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            scan = client.post(f"/workspaces/{ws_id}/scan", headers=headers).json()

        scan_id = scan["id"]
        assert client.get(f"/scans/{scan_id}", headers=headers).status_code == 200

        # Delete the workspace
        del_res = client.delete(f"/workspaces/{ws_id}", headers=headers)
        assert del_res.status_code == 204

        # Scan run must be gone
        assert client.get(f"/scans/{scan_id}", headers=headers).status_code == 404


# ===========================================================================
# 4. Data Integrity & Snapshot Immutability
# ===========================================================================

class TestDataIntegrityAndImmutability:
    """
    Adversarial verification of snapshot immutability, SHA-256 formatting,
    and API mutation rejection.
    """

    def test_sha256_hash_strict_format_and_cryptographic_parity(self, client):
        headers = create_user_and_headers(client, "integrity@tenant.com")
        ws_id, _, src_ids = setup_tenant_hierarchy(client, headers, "Integrity")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            scan = client.post(f"/workspaces/{ws_id}/scan", headers=headers).json()

        detail = client.get(f"/scans/{scan['id']}", headers=headers).json()
        snapshots = detail["snapshots"]
        assert len(snapshots) == 2

        sha256_regex = re.compile(r"^[0-9a-f]{64}$")

        for snap in snapshots:
            content_hash = snap["content_hash"]
            assert content_hash is not None
            # Must strictly be 64-char lowercase hex
            assert sha256_regex.match(content_hash), f"Invalid SHA-256 format: {content_hash}"

            # Verify cryptographic parity with normalized_content
            expected_hash = hashlib.sha256(snap["normalized_content"].encode("utf-8")).hexdigest().lower()
            assert content_hash == expected_hash, f"Hash mismatch! {content_hash} != {expected_hash}"

    def test_error_snapshots_have_null_hash_and_valid_structure(self, client):
        headers = create_user_and_headers(client, "err_integrity@tenant.com")
        ws = client.post("/workspaces", json={"name": "Err Integrity WS"}, headers=headers).json()
        comp = client.post(f"/workspaces/{ws['id']}/competitors", json={"name": "Err Comp"}, headers=headers).json()

        client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "404 Page", "url": "https://test.com/404", "source_type": "website"},
            headers=headers,
        )
        client.post(
            f"/competitors/{comp['id']}/sources",
            json={"name": "Timeout Page", "url": "https://test.com/timeout", "source_type": "website"},
            headers=headers,
        )

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            scan = client.post(f"/workspaces/{ws['id']}/scan", headers=headers).json()

        detail = client.get(f"/scans/{scan['id']}", headers=headers).json()
        for snap in detail["snapshots"]:
            assert snap["status"] == "error"
            assert snap["content_hash"] is None
            assert snap["error_message"] is not None
            assert len(snap["error_message"]) > 0
            assert isinstance(snap["response_time_ms"], int)
            assert snap["response_time_ms"] >= 0

    def test_snapshots_cannot_be_mutated_via_rest_api(self, client):
        """
        Verify that HTTP mutation verbs (PUT, PATCH, DELETE, POST) on snapshot
        resources are rejected (405 or 404), proving snapshots are append-only.
        """
        headers = create_user_and_headers(client, "immutability@tenant.com")
        ws_id, _, src_ids = setup_tenant_hierarchy(client, headers, "Immutability")
        src_id = src_ids[0]

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            scan = client.post(f"/workspaces/{ws_id}/scan", headers=headers).json()

        scan_id = scan["id"]
        detail = client.get(f"/scans/{scan_id}", headers=headers).json()
        snap_id = detail["snapshots"][0]["id"]

        mutation_attempts = [
            # Attempt to modify scan run
            ("PUT", f"/scans/{scan_id}", {"status": "tampered"}),
            ("PATCH", f"/scans/{scan_id}", {"status": "tampered"}),
            ("DELETE", f"/scans/{scan_id}", None),
            # Attempt to modify snapshot via source snapshots path
            ("PUT", f"/sources/{src_id}/snapshots", {"content": "tampered"}),
            ("POST", f"/sources/{src_id}/snapshots", {"content": "tampered"}),
            ("DELETE", f"/sources/{src_id}/snapshots", None),
            # Attempt direct snapshot endpoint manipulation
            ("PUT", f"/snapshots/{snap_id}", {"content": "tampered"}),
            ("PATCH", f"/snapshots/{snap_id}", {"content": "tampered"}),
            ("DELETE", f"/snapshots/{snap_id}", None),
        ]

        for method, path, body in mutation_attempts:
            if method == "PUT":
                res = client.put(path, json=body, headers=headers)
            elif method == "PATCH":
                res = client.patch(path, json=body, headers=headers)
            elif method == "DELETE":
                res = client.delete(path, headers=headers)
            elif method == "POST":
                res = client.post(path, json=body, headers=headers)

            assert res.status_code in (404, 405), f"{method} {path} returned {res.status_code} instead of 404/405"

    def test_repeated_scans_produce_immutable_distinct_snapshots(self, client):
        """
        Verify that successive scans never mutate previous snapshots in-place;
        they create distinct snapshot entities, preserving immutable history.
        """
        headers = create_user_and_headers(client, "append_only@tenant.com")
        ws_id, comp_id, src_ids = setup_tenant_hierarchy(client, headers, "AppendOnly")
        src_id = src_ids[0]

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_dispatcher):
            # Scan 1
            res1 = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
            scan1_id = res1.json()["id"]

            # Scan 2
            res2 = client.post(f"/workspaces/{ws_id}/scan", headers=headers)
            scan2_id = res2.json()["id"]

        detail1 = client.get(f"/scans/{scan1_id}", headers=headers).json()
        detail2 = client.get(f"/scans/{scan2_id}", headers=headers).json()

        snap1_id = [s["id"] for s in detail1["snapshots"] if s["source_id"] == src_id][0]
        snap2_id = [s["id"] for s in detail2["snapshots"] if s["source_id"] == src_id][0]

        # Snapshots must be distinct entities
        assert snap1_id != snap2_id

        # Source snapshot history must contain both distinct snapshots
        hist = client.get(f"/sources/{src_id}/snapshots", headers=headers).json()
        assert len(hist) == 2
        hist_ids = [s["id"] for s in hist]
        assert snap1_id in hist_ids
        assert snap2_id in hist_ids
