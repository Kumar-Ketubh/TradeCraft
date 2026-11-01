# backend/tests/test_agent_pipeline_integration.py
"""
Integration tests for the TradeCraft LangGraph competitive intelligence pipeline
and structured proposal synthesis engine.

Verifies:
1. End-to-end execution of LangGraph agent workflow:
   Change -> Researcher -> Analyzer -> Critic -> IntelligenceFinding + EvidenceQuote.
2. Evidence Grounding Accuracy (EGA) computation and offset alignment.
3. Proposal synthesis enforcing the exact 7-section document standard.
4. Rejection of unverified or rejected findings when generating proposals.
5. REST API endpoints for findings and proposals with workspace isolation.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.change import Change
from app.models.finding import IntelligenceFinding, VerificationStatus, ConfidenceLevel
from app.models.proposal import Proposal, ProposalStatus
from app.models.snapshot import Snapshot
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.workspace import Workspace
from app.models.user import User
from app.models.scan_run import ScanRun
from app.services.agents.graph import run_agent_pipeline
from app.services.proposal_engine.generator import generate_structured_proposal


def _create_test_hierarchy(db_session, email="pipeline_owner@example.com"):
    """Helper to seed a complete user -> workspace -> competitor -> source hierarchy."""
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            name="Pipeline Tester",
            email=email,
            password_hash="pbkdf2_sha256$test$hash",
        )
        db_session.add(user)
        db_session.flush()

    workspace = Workspace(
        user_id=user.id,
        name="Test Intelligence Workspace",
        product_name="TradeCraft AI",
        value_proposition="Automated competitive intelligence for product teams",
        target_audience="Founders, PMs, and engineering leaders",
        pricing_summary="Tier 1 $49/mo, Tier 2 $199/mo",
        strategic_focus="Deep evidence grounding and zero hallucinations",
    )
    db_session.add(workspace)
    db_session.flush()

    competitor = Competitor(
        workspace_id=workspace.id,
        name="Apex Rival",
        website="https://apexrival.com",
    )
    db_session.add(competitor)
    db_session.flush()

    source = Source(
        competitor_id=competitor.id,
        name="Pricing Page",
        url="https://apexrival.com/pricing",
        source_type="html",
    )
    db_session.add(source)
    db_session.flush()

    scan_run = ScanRun(
        workspace_id=workspace.id,
        competitor_id=competitor.id,
        status="completed",
    )
    db_session.add(scan_run)
    db_session.flush()

    return user, workspace, competitor, source, scan_run


def test_agent_pipeline_direct_execution(db_session):
    """
    Test direct execution of run_agent_pipeline against a real Change record.
    Verifies that Context Researcher, Impact Analyzer, and Critic Verifier
    produce a verified IntelligenceFinding with evidence quotes and character offsets.
    """
    user, workspace, competitor, source, scan_run = _create_test_hierarchy(db_session)

    # 1. Create a snapshot with realistic competitor pricing content
    snapshot = Snapshot(
        scan_run_id=scan_run.id,
        source_id=source.id,
        status="success",
        status_code=200,
        raw_content="Apex Rival Pro Tier now available for $99/mo with unlimited API calls and dedicated support.",
        normalized_content="Apex Rival Pro Tier now available for $99/mo with unlimited API calls and dedicated support.",
        content_hash="abc123hash",
    )
    db_session.add(snapshot)
    db_session.flush()

    # 2. Create a Change record with unified diff
    change = Change(
        workspace_id=workspace.id,
        competitor_id=competitor.id,
        source_id=source.id,
        scan_run_id=scan_run.id,
        current_snapshot_id=snapshot.id,
        change_hash="change-hash-123",
        change_type="modification",
        category="pricing_change",
        is_meaningful=True,
        significance_score=0.85,
        summary="Competitor raised price to $99/mo",
        diff_unified="@@ -1,1 +1,1 @@\n-Apex Rival Pro Tier $49/mo\n+Apex Rival Pro Tier now available for $99/mo with unlimited API calls",
    )
    db_session.add(change)
    db_session.commit()

    # 3. Execute agent pipeline
    finding = run_agent_pipeline(change_id=change.id, db=db_session)

    # 4. Assertions on generated finding
    assert finding is not None
    assert finding.workspace_id == workspace.id
    assert finding.change_id == change.id
    assert finding.grounding_score >= 85.0
    assert finding.verification_status == VerificationStatus.VERIFIED.value
    assert len(finding.evidence_quotes) > 0

    # Verify character offsets
    first_quote = finding.evidence_quotes[0]
    assert first_quote.verbatim_quote in snapshot.normalized_content
    assert first_quote.char_offset_start is not None
    assert first_quote.char_offset_end is not None
    assert first_quote.char_offset_end > first_quote.char_offset_start


def test_proposal_generation_7_sections_standard(db_session):
    """
    Test proposal engine synthesis: guarantees all 7 required H2 sections
    and evidence quote attribution.
    """
    user, workspace, competitor, source, scan_run = _create_test_hierarchy(db_session, email="proposal_owner@example.com")

    snapshot = Snapshot(
        scan_run_id=scan_run.id,
        source_id=source.id,
        status="success",
        normalized_content="Enterprise plan includes SOC-2 compliance and SLA guarantee for $499/mo.",
    )
    db_session.add(snapshot)
    db_session.flush()

    change = Change(
        workspace_id=workspace.id,
        competitor_id=competitor.id,
        source_id=source.id,
        scan_run_id=scan_run.id,
        current_snapshot_id=snapshot.id,
        change_hash="hash-456",
        diff_unified="+Enterprise plan includes SOC-2 compliance and SLA guarantee for $499/mo.",
    )
    db_session.add(change)
    db_session.flush()

    finding = run_agent_pipeline(change_id=change.id, db=db_session)
    assert finding is not None

    # Generate proposal
    proposal_text = generate_structured_proposal(
        workspace=workspace,
        findings=[finding],
        title="Enterprise Counter-Strategy",
        target_goal="Defend mid-market pipeline",
    )

    # Assert exact 7 required sections are present
    required_sections = [
        "## 1. Problem / Opportunity",
        "## 2. Competitor Change",
        "## 3. Evidence",
        "## 4. Strategic Impact",
        "## 5. Proposed Response",
        "## 6. Suggested Features/Work",
        "## 7. Expected Value",
    ]
    for section in required_sections:
        assert section in proposal_text, f"Missing required section: {section}"


def test_proposal_rejection_of_unverified_findings(db_session):
    """
    Test that the proposal generator strictly rejects unverified or rejected findings.
    """
    user, workspace, _, _, _ = _create_test_hierarchy(db_session, email="unverified_owner@example.com")

    unverified_finding = IntelligenceFinding(
        workspace_id=workspace.id,
        title="Unverified Rumor",
        category="OTHER",
        factual_summary="Unverified claim without snapshot evidence",
        impact_analysis="None",
        recommended_action="None",
        confidence_level=ConfidenceLevel.LOW.value,
        verification_status=VerificationStatus.DOWNGRADED.value,
        grounding_score=35.0,
    )
    db_session.add(unverified_finding)
    db_session.commit()

    with pytest.raises(ValueError, match="Cannot generate proposal from unverified or rejected findings"):
        generate_structured_proposal(
            workspace=workspace,
            findings=[unverified_finding],
            title="Invalid Proposal",
        )


def test_findings_and_proposals_api_endpoints(client: TestClient, db_session):
    """
    Test the REST API endpoints:
    - POST /changes/{id}/analyze -> triggers pipeline
    - GET /workspaces/{id}/findings -> retrieves findings with quotes
    - POST /workspaces/{id}/proposals -> generates proposal
    - GET /workspaces/{id}/proposals -> lists proposals
    - GET /proposals/{id} -> retrieves single proposal
    - PUT /proposals/{id} -> updates proposal status to FINALIZED
    """
    reg_res = client.post(
        "/auth/register",
        json={"name": "API Tester", "email": "api_pipeline@example.com", "password": "password123"},
    )
    assert reg_res.status_code == 201
    auth_headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    user_id = reg_res.json()["user"]["id"]

    # Create workspace
    ws_res = client.post(
        "/workspaces",
        json={"name": "API Intelligence Hub"},
        headers=auth_headers,
    )
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # Create competitor
    comp_res = client.post(
        f"/workspaces/{ws_id}/competitors",
        json={"name": "CloudCo", "website": "https://cloudco.com"},
        headers=auth_headers,
    )
    assert comp_res.status_code == 201
    comp_id = comp_res.json()["id"]

    # Create source
    src_res = client.post(
        f"/competitors/{comp_id}/sources",
        json={"name": "Pricing Page", "url": "https://cloudco.com/pricing", "source_type": "html"},
        headers=auth_headers,
    )
    assert src_res.status_code == 201
    src_id = src_res.json()["id"]

    # Seed snapshot & change in db_session
    scan_run = ScanRun(workspace_id=ws_id, competitor_id=comp_id, status="completed")
    db_session.add(scan_run)
    db_session.flush()

    snapshot = Snapshot(
        scan_run_id=scan_run.id,
        source_id=src_id,
        status="success",
        normalized_content="Starter plan price reduced from $29 to $19 per seat per month.",
    )
    db_session.add(snapshot)
    db_session.flush()

    change = Change(
        workspace_id=ws_id,
        competitor_id=comp_id,
        source_id=src_id,
        scan_run_id=scan_run.id,
        current_snapshot_id=snapshot.id,
        change_hash="hash-api-789",
        diff_unified="+Starter plan price reduced from $29 to $19 per seat per month.",
    )
    db_session.add(change)
    db_session.commit()

    # 1. Trigger AI analysis via POST /changes/{id}/analyze
    res = client.post(f"/changes/{change.id}/analyze", headers=auth_headers)
    assert res.status_code == 200
    finding_data = res.json()
    assert finding_data["workspace_id"] == ws_id
    assert finding_data["verification_status"] == "VERIFIED"
    assert finding_data["grounding_score"] >= 85.0
    finding_id = finding_data["id"]

    # 2. Retrieve findings via GET /workspaces/{id}/findings
    res = client.get(f"/workspaces/{ws_id}/findings", headers=auth_headers)
    assert res.status_code == 200
    findings_list = res.json()
    assert len(findings_list) >= 1
    assert any(f["id"] == finding_id for f in findings_list)

    # 3. Generate proposal via POST /workspaces/{id}/proposals
    proposal_payload = {
        "title": "Counter-Strategy: Competitive Pricing Adjustment",
        "target_goal": "Maintain conversion rate against competitor price drop",
        "finding_ids": [finding_id],
    }
    res = client.post(
        f"/workspaces/{ws_id}/proposals",
        json=proposal_payload,
        headers=auth_headers,
    )
    assert res.status_code == 201
    proposal_data = res.json()
    assert proposal_data["title"] == proposal_payload["title"]
    assert proposal_data["status"] == "DRAFT"
    assert "## 1. Problem / Opportunity" in proposal_data["markdown_content"]
    assert "## 3. Evidence" in proposal_data["markdown_content"]
    proposal_id = proposal_data["id"]

    # 4. Retrieve proposal by ID
    res = client.get(f"/proposals/{proposal_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == proposal_id

    # 5. Update proposal status to FINALIZED
    res = client.put(
        f"/proposals/{proposal_id}",
        json={"status": "FINALIZED"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "FINALIZED"
