# backend/tests/test_change_service.py
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.models.change import Change
from app.services.change_service import ChangeDetectionService
from app.diff.engine import DiffEngine, compute_change_hash


def create_test_hierarchy(db: Session):
    """Helper to create User -> Workspace -> Competitor -> Source hierarchy."""
    user = User(
        name="Test Analyst",
        email=f"analyst_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="hashed_pw",
    )
    db.add(user)
    db.flush()

    workspace = Workspace(user_id=user.id, name="Competitor Intelligence")
    db.add(workspace)
    db.flush()

    competitor = Competitor(
        workspace_id=workspace.id,
        name="SaaS Rival Corp",
        website="https://rival.example.com",
    )
    db.add(competitor)
    db.flush()

    source = Source(
        competitor_id=competitor.id,
        name="Pricing & Packaging",
        url="https://rival.example.com/pricing",
        source_type="pricing",
    )
    db.add(source)
    db.flush()

    return user, workspace, competitor, source


def test_baseline_first_scan_produces_no_changes(db_session):
    """Baseline scan on a new source should produce zero changes."""
    user, workspace, competitor, source = create_test_hierarchy(db_session)

    scan_run = ScanRun(
        workspace_id=workspace.id,
        competitor_id=competitor.id,
        status="completed",
        total_sources=1,
        successful_sources=1,
    )
    db_session.add(scan_run)
    db_session.flush()

    content = "Welcome to Rival Corp\nPro Plan: $49/mo"
    content_hash = compute_change_hash(content)

    snapshot = Snapshot(
        scan_run_id=scan_run.id,
        source_id=source.id,
        status="success",
        status_code=200,
        raw_content=f"<html><body>{content}</body></html>",
        normalized_content=content,
        content_hash=content_hash,
    )
    db_session.add(snapshot)
    db_session.flush()

    service = ChangeDetectionService(db=db_session)
    change = service.detect_change_for_snapshot(snapshot)

    assert change is None
    assert db_session.query(Change).count() == 0


def test_unchanged_content_fast_path_produces_no_changes(db_session):
    """Successive scan with identical content hash returns None via fast-path."""
    user, workspace, competitor, source = create_test_hierarchy(db_session)
    t0 = datetime.now(timezone.utc) - timedelta(hours=2)
    t1 = datetime.now(timezone.utc)

    # Scan 1
    s1 = ScanRun(workspace_id=workspace.id, competitor_id=competitor.id, status="completed", created_at=t0)
    db_session.add(s1)
    db_session.flush()

    content = "Pro Plan: $49/mo\nIncludes 10 user seats\nUnlimited projects"
    h = compute_change_hash(content)

    snap1 = Snapshot(
        scan_run_id=s1.id,
        source_id=source.id,
        status="success",
        status_code=200,
        normalized_content=content,
        content_hash=h,
        created_at=t0,
    )
    db_session.add(snap1)
    db_session.flush()

    # Scan 2: Identical content
    s2 = ScanRun(workspace_id=workspace.id, competitor_id=competitor.id, status="completed", created_at=t1)
    db_session.add(s2)
    db_session.flush()

    snap2 = Snapshot(
        scan_run_id=s2.id,
        source_id=source.id,
        status="success",
        status_code=200,
        normalized_content=content,
        content_hash=h,
        created_at=t1,
    )
    db_session.add(snap2)
    db_session.flush()

    service = ChangeDetectionService(db=db_session)
    change = service.detect_change_for_snapshot(snap2)

    assert change is None
    assert db_session.query(Change).count() == 0


def test_modified_content_creates_change_record_linked_to_snapshots(db_session):
    """Substantive modification produces a Change record linked to both snapshots."""
    user, workspace, competitor, source = create_test_hierarchy(db_session)
    t0 = datetime.now(timezone.utc) - timedelta(hours=1)
    t1 = datetime.now(timezone.utc)

    # Scan 1: Baseline
    s1 = ScanRun(workspace_id=workspace.id, status="completed", created_at=t0)
    db_session.add(s1)
    db_session.flush()

    old_content = "Pro Plan: $49/mo\nIncludes 5 seats\nStandard Support"
    snap1 = Snapshot(
        scan_run_id=s1.id,
        source_id=source.id,
        status="success",
        status_code=200,
        normalized_content=old_content,
        content_hash=compute_change_hash(old_content),
        created_at=t0,
    )
    db_session.add(snap1)
    db_session.flush()

    # Scan 2: Price increase
    s2 = ScanRun(workspace_id=workspace.id, status="completed", created_at=t1)
    db_session.add(s2)
    db_session.flush()

    new_content = "Pro Plan: $89/mo\nIncludes 10 seats\nPriority 24/7 Support"
    snap2 = Snapshot(
        scan_run_id=s2.id,
        source_id=source.id,
        status="success",
        status_code=200,
        normalized_content=new_content,
        content_hash=compute_change_hash(new_content),
        created_at=t1,
    )
    db_session.add(snap2)
    db_session.flush()

    service = ChangeDetectionService(db=db_session)
    change = service.detect_change_for_snapshot(snap2)

    assert change is not None
    assert change.id is not None
    assert change.previous_snapshot_id == snap1.id
    assert change.current_snapshot_id == snap2.id
    assert change.workspace_id == workspace.id
    assert change.competitor_id == competitor.id
    assert change.source_id == source.id
    assert change.scan_run_id == s2.id
    assert len(change.change_hash) == 64
    assert change.category == "pricing_change"
    assert change.is_meaningful is True
    assert change.significance_score >= 0.70
    assert "-Pro Plan: $49/mo" in change.diff_unified
    assert "+Pro Plan: $89/mo" in change.diff_unified
    assert change.diff_stats is not None
    assert change.diff_stats["lines_added"] >= 1
    assert change.diff_stats["lines_removed"] >= 1


def test_noise_change_is_classified_as_not_meaningful(db_session):
    """Cosmetic changes like copyright roll-forward are flagged as noise."""
    user, workspace, competitor, source = create_test_hierarchy(db_session)
    t0 = datetime.now(timezone.utc) - timedelta(hours=2)
    t1 = datetime.now(timezone.utc)

    s1 = ScanRun(workspace_id=workspace.id, status="completed", created_at=t0)
    s2 = ScanRun(workspace_id=workspace.id, status="completed", created_at=t1)
    db_session.add_all([s1, s2])
    db_session.flush()

    old_content = "About Acme Inc\nCopyright 2024 Acme Inc\nAll rights reserved."
    new_content = "About Acme Inc\nCopyright 2025 Acme Inc\nAll rights reserved."

    snap1 = Snapshot(
        scan_run_id=s1.id,
        source_id=source.id,
        status="success",
        normalized_content=old_content,
        content_hash=compute_change_hash(old_content),
        created_at=t0,
    )
    snap2 = Snapshot(
        scan_run_id=s2.id,
        source_id=source.id,
        status="success",
        normalized_content=new_content,
        content_hash=compute_change_hash(new_content),
        created_at=t1,
    )
    db_session.add_all([snap1, snap2])
    db_session.flush()

    service = ChangeDetectionService(db=db_session)
    change = service.detect_change_for_snapshot(snap2)

    assert change is not None
    assert change.is_meaningful is False
    assert change.category == "noise"
    assert change.significance_score == 0.0


def test_prior_snapshot_resolution_ignores_errors_and_picks_latest_success(db_session):
    """Prior snapshot lookup skips failed snapshots and picks the latest success."""
    user, workspace, competitor, source = create_test_hierarchy(db_session)
    now = datetime.now(timezone.utc)

    # 1. Success snapshot at t - 3h
    s1 = ScanRun(workspace_id=workspace.id, status="completed", created_at=now - timedelta(hours=3))
    db_session.add(s1)
    db_session.flush()
    snap1 = Snapshot(
        scan_run_id=s1.id,
        source_id=source.id,
        status="success",
        normalized_content="Version 1",
        content_hash="h1",
        created_at=now - timedelta(hours=3),
    )
    db_session.add(snap1)

    # 2. Success snapshot at t - 2h (should be selected as prior baseline)
    s2 = ScanRun(workspace_id=workspace.id, status="completed", created_at=now - timedelta(hours=2))
    db_session.add(s2)
    db_session.flush()
    snap2 = Snapshot(
        scan_run_id=s2.id,
        source_id=source.id,
        status="success",
        normalized_content="Version 2",
        content_hash="h2",
        created_at=now - timedelta(hours=2),
    )
    db_session.add(snap2)

    # 3. Error snapshot at t - 1h (must be ignored)
    s3 = ScanRun(workspace_id=workspace.id, status="completed", created_at=now - timedelta(hours=1))
    db_session.add(s3)
    db_session.flush()
    snap3 = Snapshot(
        scan_run_id=s3.id,
        source_id=source.id,
        status="error",
        error_message="HTTP 500 Server Error",
        created_at=now - timedelta(hours=1),
    )
    db_session.add(snap3)

    # 4. Current snapshot at t
    s4 = ScanRun(workspace_id=workspace.id, status="completed", created_at=now)
    db_session.add(s4)
    db_session.flush()
    snap4 = Snapshot(
        scan_run_id=s4.id,
        source_id=source.id,
        status="success",
        normalized_content="Version 3",
        content_hash="h3",
        created_at=now,
    )
    db_session.add(snap4)
    db_session.flush()

    service = ChangeDetectionService(db=db_session)
    prior = service.get_prior_successful_snapshot(snap4)

    assert prior is not None
    assert prior.id == snap2.id
    assert prior.status == "success"
    assert prior.normalized_content == "Version 2"


def test_error_and_empty_snapshots_return_none(db_session):
    """Snapshots with error status or missing content return None."""
    user, workspace, competitor, source = create_test_hierarchy(db_session)
    s1 = ScanRun(workspace_id=workspace.id, status="completed")
    db_session.add(s1)
    db_session.flush()

    snap_err = Snapshot(
        scan_run_id=s1.id,
        source_id=source.id,
        status="error",
        error_message="Connection timed out",
    )
    db_session.add(snap_err)
    db_session.flush()

    service = ChangeDetectionService(db=db_session)
    assert service.detect_change_for_snapshot(snap_err) is None


def test_detect_changes_for_scan_run_batch(db_session):
    """detect_changes_for_scan_run processes all snapshots in a scan run."""
    user, workspace, competitor, source = create_test_hierarchy(db_session)
    now = datetime.now(timezone.utc)

    # Baseline scan
    s1 = ScanRun(workspace_id=workspace.id, created_at=now - timedelta(hours=1))
    db_session.add(s1)
    db_session.flush()
    snap1 = Snapshot(
        scan_run_id=s1.id,
        source_id=source.id,
        status="success",
        normalized_content="Feature A is available.",
        content_hash=compute_change_hash("Feature A is available."),
        created_at=now - timedelta(hours=1),
    )
    db_session.add(snap1)
    db_session.flush()

    # Second scan with update
    s2 = ScanRun(workspace_id=workspace.id, created_at=now)
    db_session.add(s2)
    db_session.flush()
    snap2 = Snapshot(
        scan_run_id=s2.id,
        source_id=source.id,
        status="success",
        normalized_content="Feature A and Feature B are now available. Introducing Version 2.0!",
        content_hash=compute_change_hash("Feature A and Feature B are now available. Introducing Version 2.0!"),
        created_at=now,
    )
    db_session.add(snap2)
    db_session.flush()

    service = ChangeDetectionService(db=db_session)
    detected = service.detect_changes_for_scan_run(s2.id)

    assert len(detected) == 1
    assert detected[0].category == "feature_announcement"
    assert detected[0].is_meaningful is True
