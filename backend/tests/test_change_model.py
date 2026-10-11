# backend/tests/test_change_model.py
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import inspect

from app.models.user import User
from app.models.workspace import Workspace
from app.models.competitor import Competitor
from app.models.source import Source
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.models.change import Change


def create_test_hierarchy(db_session):
    """Helper to create a complete hierarchy up to two snapshots."""
    user = User(
        name="Test User",
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="fakehash",
    )
    db_session.add(user)
    db_session.flush()

    workspace = Workspace(
        user_id=user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    db_session.flush()

    competitor = Competitor(
        workspace_id=workspace.id,
        name="Test Competitor",
        website="https://competitor.com",
    )
    db_session.add(competitor)
    db_session.flush()

    source = Source(
        competitor_id=competitor.id,
        name="Pricing Page",
        url="https://competitor.com/pricing",
        source_type="pricing",
    )
    db_session.add(source)
    db_session.flush()

    scan_run = ScanRun(
        workspace_id=workspace.id,
        competitor_id=competitor.id,
        status="completed",
        total_sources=1,
        successful_sources=1,
    )
    db_session.add(scan_run)
    db_session.flush()

    snap_prev = Snapshot(
        scan_run_id=scan_run.id,
        source_id=source.id,
        status="success",
        status_code=200,
        raw_content="<html>$29/mo</html>",
        normalized_content="$29/mo",
        content_hash="a" * 64,
    )
    snap_curr = Snapshot(
        scan_run_id=scan_run.id,
        source_id=source.id,
        status="success",
        status_code=200,
        raw_content="<html>$39/mo</html>",
        normalized_content="$39/mo",
        content_hash="b" * 64,
    )
    db_session.add_all([snap_prev, snap_curr])
    db_session.flush()

    return {
        "user": user,
        "workspace": workspace,
        "competitor": competitor,
        "source": source,
        "scan_run": scan_run,
        "snap_prev": snap_prev,
        "snap_curr": snap_curr,
    }


def test_create_change_record_with_all_fields_and_relationships(db_session):
    """Test creating a Change record with all 16 fields and verifying all relationships."""
    h = create_test_hierarchy(db_session)
    now = datetime.now(timezone.utc)

    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="c" * 64,
        change_type="modification",
        category="pricing_change",
        is_meaningful=True,
        significance_score=0.92,
        summary="Pricing tier changed from $29 to $39 per month.",
        diff_unified="--- a/pricing\n+++ b/pricing\n@@ -1 +1 @@\n-$29/mo\n+$39/mo\n",
        diff_stats={
            "lines_added": 1,
            "lines_removed": 1,
            "chars_added": 7,
            "chars_removed": 7,
            "similarity_ratio": 0.82,
        },
        detected_at=now,
    )
    db_session.add(change)
    db_session.commit()

    # Query back
    fetched = db_session.query(Change).filter(Change.id == change.id).first()
    assert fetched is not None
    assert fetched.id == change.id
    assert fetched.workspace_id == h["workspace"].id
    assert fetched.competitor_id == h["competitor"].id
    assert fetched.source_id == h["source"].id
    assert fetched.scan_run_id == h["scan_run"].id
    assert fetched.previous_snapshot_id == h["snap_prev"].id
    assert fetched.current_snapshot_id == h["snap_curr"].id
    assert fetched.change_hash == "c" * 64
    assert fetched.change_type == "modification"
    assert fetched.category == "pricing_change"
    assert fetched.is_meaningful is True
    assert pytest.approx(fetched.significance_score, 0.001) == 0.92
    assert fetched.summary == "Pricing tier changed from $29 to $39 per month."
    assert "--- a/pricing" in fetched.diff_unified
    assert fetched.diff_stats["lines_added"] == 1
    assert fetched.diff_stats["lines_removed"] == 1
    assert fetched.detected_at is not None
    fetched_dt = fetched.detected_at if fetched.detected_at.tzinfo else fetched.detected_at.replace(tzinfo=timezone.utc)
    assert fetched_dt == now

    # Forward relationship navigation
    assert fetched.workspace == h["workspace"]
    assert fetched.competitor == h["competitor"]
    assert fetched.source == h["source"]
    assert fetched.scan_run == h["scan_run"]
    assert fetched.previous_snapshot == h["snap_prev"]
    assert fetched.current_snapshot == h["snap_curr"]

    # Back-populates navigation
    assert change in h["workspace"].changes
    assert change in h["competitor"].changes
    assert change in h["source"].changes
    assert change in h["scan_run"].changes
    assert change in h["snap_curr"].changes
    assert change in h["snap_prev"].changes_as_previous


def test_change_defaults_and_nullable_previous_snapshot(db_session):
    """Test default values on Change and nullable previous_snapshot_id for initial baselines."""
    h = create_test_hierarchy(db_session)

    # Change with minimal required fields and no previous snapshot
    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=None,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="d" * 64,
        diff_unified="+++ b/new_content\n@@ -0,0 +1 @@\n+Initial content\n",
    )
    db_session.add(change)
    db_session.commit()

    fetched = db_session.query(Change).filter(Change.id == change.id).first()
    assert fetched is not None
    assert fetched.previous_snapshot_id is None
    assert fetched.previous_snapshot is None
    assert fetched.change_type == "modification"
    assert fetched.category == "unknown"
    assert fetched.is_meaningful is True
    assert fetched.significance_score == 0.0
    assert fetched.summary is None
    assert fetched.diff_stats is None
    assert fetched.detected_at is not None
    assert fetched.current_snapshot == h["snap_curr"]
    assert change in h["snap_curr"].changes


def test_dual_snapshot_navigation(db_session):
    """Test dual snapshot navigation (snapshot.changes vs snapshot.changes_as_previous)."""
    h = create_test_hierarchy(db_session)

    # Create a third snapshot
    snap3 = Snapshot(
        scan_run_id=h["scan_run"].id,
        source_id=h["source"].id,
        status="success",
        status_code=200,
        raw_content="<html>$49/mo</html>",
        normalized_content="$49/mo",
        content_hash="c" * 64,
    )
    db_session.add(snap3)
    db_session.flush()

    # Change 1: snap_prev -> snap_curr
    change1 = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="1" * 64,
        diff_unified="diff1",
    )
    # Change 2: snap_curr -> snap3
    change2 = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_curr"].id,
        current_snapshot_id=snap3.id,
        change_hash="2" * 64,
        diff_unified="diff2",
    )
    db_session.add_all([change1, change2])
    db_session.commit()

    # Refresh instances
    db_session.refresh(h["snap_prev"])
    db_session.refresh(h["snap_curr"])
    db_session.refresh(snap3)

    # snap_prev was only previous, never current
    assert h["snap_prev"].changes == []
    assert h["snap_prev"].changes_as_previous == [change1]

    # snap_curr was current for change1 and previous for change2
    assert h["snap_curr"].changes == [change1]
    assert h["snap_curr"].changes_as_previous == [change2]

    # snap3 was only current, never previous
    assert snap3.changes == [change2]
    assert snap3.changes_as_previous == []


def test_cascade_delete_workspace(db_session):
    """Deleting a workspace cascades to delete all associated Change records."""
    h = create_test_hierarchy(db_session)
    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="w" * 64,
        diff_unified="diff_w",
    )
    db_session.add(change)
    db_session.commit()
    change_id = change.id

    db_session.delete(h["workspace"])
    db_session.commit()

    assert db_session.query(Change).filter(Change.id == change_id).first() is None


def test_cascade_delete_competitor(db_session):
    """Deleting a competitor cascades to delete all associated Change records."""
    h = create_test_hierarchy(db_session)
    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="c" * 64,
        diff_unified="diff_c",
    )
    db_session.add(change)
    db_session.commit()
    change_id = change.id

    db_session.delete(h["competitor"])
    db_session.commit()

    assert db_session.query(Change).filter(Change.id == change_id).first() is None


def test_cascade_delete_source(db_session):
    """Deleting a source cascades to delete all associated Change records."""
    h = create_test_hierarchy(db_session)
    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="s" * 64,
        diff_unified="diff_s",
    )
    db_session.add(change)
    db_session.commit()
    change_id = change.id

    db_session.delete(h["source"])
    db_session.commit()

    assert db_session.query(Change).filter(Change.id == change_id).first() is None


def test_cascade_delete_scan_run(db_session):
    """Deleting a scan_run cascades to delete all associated Change records."""
    h = create_test_hierarchy(db_session)
    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="r" * 64,
        diff_unified="diff_r",
    )
    db_session.add(change)
    db_session.commit()
    change_id = change.id

    db_session.delete(h["scan_run"])
    db_session.commit()

    assert db_session.query(Change).filter(Change.id == change_id).first() is None


def test_cascade_delete_current_snapshot(db_session):
    """Deleting the current snapshot cascades to delete associated Change records."""
    h = create_test_hierarchy(db_session)
    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="n" * 64,
        diff_unified="diff_n",
    )
    db_session.add(change)
    db_session.commit()
    change_id = change.id

    db_session.delete(h["snap_curr"])
    db_session.commit()

    assert db_session.query(Change).filter(Change.id == change_id).first() is None


def test_cascade_delete_previous_snapshot(db_session):
    """Deleting the previous snapshot cascades to delete associated Change records."""
    h = create_test_hierarchy(db_session)
    change = Change(
        workspace_id=h["workspace"].id,
        competitor_id=h["competitor"].id,
        source_id=h["source"].id,
        scan_run_id=h["scan_run"].id,
        previous_snapshot_id=h["snap_prev"].id,
        current_snapshot_id=h["snap_curr"].id,
        change_hash="p" * 64,
        diff_unified="diff_p",
    )
    db_session.add(change)
    db_session.commit()
    change_id = change.id

    db_session.delete(h["snap_prev"])
    db_session.commit()

    assert db_session.query(Change).filter(Change.id == change_id).first() is None


def test_changes_table_schema_and_indexes(db_session):
    """Verify changes table schema, foreign keys, and indexes via SQLAlchemy inspection."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    assert "changes" in tables

    columns = {col["name"]: col for col in inspector.get_columns("changes")}
    expected_cols = [
        "id",
        "workspace_id",
        "competitor_id",
        "source_id",
        "scan_run_id",
        "previous_snapshot_id",
        "current_snapshot_id",
        "change_hash",
        "change_type",
        "category",
        "is_meaningful",
        "significance_score",
        "summary",
        "diff_unified",
        "diff_stats",
        "detected_at",
    ]
    for col_name in expected_cols:
        assert col_name in columns, f"Column {col_name} missing from changes table"

    # Foreign keys
    fk_list = inspector.get_foreign_keys("changes")
    fk_referred_tables = {fk["referred_table"] for fk in fk_list}
    assert "workspaces" in fk_referred_tables
    assert "competitors" in fk_referred_tables
    assert "sources" in fk_referred_tables
    assert "scan_runs" in fk_referred_tables
    assert "snapshots" in fk_referred_tables

    # Indexes
    indexes = inspector.get_indexes("changes")
    indexed_columns = set()
    for idx in indexes:
        indexed_columns.update(idx["column_names"])

    required_indexed_cols = {
        "workspace_id",
        "competitor_id",
        "source_id",
        "scan_run_id",
        "previous_snapshot_id",
        "current_snapshot_id",
        "change_hash",
        "change_type",
        "category",
        "is_meaningful",
        "detected_at",
    }
    assert required_indexed_cols.issubset(indexed_columns)


def test_alembic_migration_upgrade_downgrade(tmp_path, monkeypatch):
    """Programmatically verify Alembic migration upgrade to head and downgrade to 7a8b9c0d1e2f."""
    import os
    from alembic.config import Config
    from alembic import command

    db_path = tmp_path / "alembic_test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    alembic_cfg = Config(alembic_cfg_path)
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option(
        "script_location",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic")),
    )

    # Upgrade to head (should apply 8c9d0e1f2a3b)
    command.upgrade(alembic_cfg, "head")

    from sqlalchemy import create_engine
    test_engine = create_engine(db_url)
    inspector = inspect(test_engine)
    assert "changes" in inspector.get_table_names()
    idx_names = {idx["name"] for idx in inspector.get_indexes("changes")}
    assert "ix_changes_workspace_id" in idx_names
    assert "ix_changes_change_hash" in idx_names
    assert "ix_changes_category" in idx_names

    # Downgrade to down_revision 7a8b9c0d1e2f
    command.downgrade(alembic_cfg, "7a8b9c0d1e2f")
    inspector = inspect(test_engine)
    assert "changes" not in inspector.get_table_names()
    assert "snapshots" in inspector.get_table_names()

    # Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(test_engine)
    assert "changes" in inspector.get_table_names()

