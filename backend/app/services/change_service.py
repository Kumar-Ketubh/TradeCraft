# backend/app/services/change_service.py
"""
Change detection service for TradeCraft competitive intelligence.

Compares newly captured source snapshots against prior successful baselines,
computes deterministic unified diffs and hashes, performs meaningfulness
classification and categorization, and persists Change records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.classifiers.meaningfulness import MeaningfulnessClassifier
from app.diff.engine import DiffEngine
from app.models.change import Change
from app.models.competitor import Competitor
from app.models.scan_run import ScanRun
from app.models.snapshot import Snapshot
from app.models.source import Source

logger = logging.getLogger(__name__)


class ChangeDetectionService:
    """
    Evaluates newly captured snapshots against prior historical baselines
    to detect, classify, and persist changes.
    """

    def __init__(
        self,
        db: Session,
        diff_engine: Optional[DiffEngine] = None,
        classifier: Optional[MeaningfulnessClassifier] = None,
    ):
        self.db = db
        self.diff_engine = diff_engine or DiffEngine()
        self.classifier = classifier or MeaningfulnessClassifier()

    def get_prior_successful_snapshot(
        self, current_snapshot: Snapshot
    ) -> Optional[Snapshot]:
        """
        Find the most recent prior successful snapshot of the same source.
        Excludes the current snapshot and any snapshot from the same scan run.
        """
        query = (
            self.db.query(Snapshot)
            .filter(
                Snapshot.source_id == current_snapshot.source_id,
                Snapshot.status == "success",
                Snapshot.id != current_snapshot.id,
            )
        )
        if current_snapshot.scan_run_id:
            query = query.filter(Snapshot.scan_run_id != current_snapshot.scan_run_id)
        if current_snapshot.created_at:
            query = query.filter(Snapshot.created_at <= current_snapshot.created_at)

        return query.order_by(Snapshot.created_at.desc(), Snapshot.id.desc()).first()

    def detect_change_for_snapshot(
        self, current_snapshot: Snapshot
    ) -> Optional[Change]:
        """
        Detect, diff, classify, and persist a change for a newly captured snapshot.

        Returns:
            Change instance if a substantive difference was detected, or None
            if the snapshot represents a baseline, unchanged content, or invalid state.
        """
        # 1. Only successful snapshots with normalized content can be compared
        if (
            current_snapshot.status != "success"
            or current_snapshot.normalized_content is None
        ):
            return None

        # 2. Look up prior successful baseline snapshot
        prior_snapshot = self.get_prior_successful_snapshot(current_snapshot)
        if prior_snapshot is None:
            # Baseline snapshot (first successful scan of this source) - no change to compare against
            return None

        # 3. Fast-path check: identical non-empty content hashes guarantee zero changes
        if (
            current_snapshot.content_hash
            and prior_snapshot.content_hash
            and current_snapshot.content_hash == prior_snapshot.content_hash
        ):
            return None

        # 4. Compute line-by-line unified diff and statistics
        old_content = prior_snapshot.normalized_content or ""
        new_content = current_snapshot.normalized_content or ""
        diff_result = self.diff_engine.compute_diff(old_content, new_content)

        if diff_result.is_empty or not diff_result.diff_unified.strip():
            return None

        # 5. Classify diff for meaningfulness, category, and significance score
        classification = self.classifier.classify(
            diff_unified=diff_result.diff_unified,
            diff_stats=diff_result.diff_stats,
            old_text=old_content,
            new_text=new_content,
        )

        # 6. Retrieve parent hierarchy (source -> competitor -> workspace)
        source = (
            current_snapshot.source
            or self.db.query(Source).filter(Source.id == current_snapshot.source_id).first()
        )
        if not source:
            logger.warning(
                f"Source {current_snapshot.source_id} not found for snapshot {current_snapshot.id}"
            )
            return None

        competitor_id = source.competitor_id
        competitor = (
            source.competitor
            or self.db.query(Competitor).filter(Competitor.id == competitor_id).first()
        )
        workspace_id = competitor.workspace_id if competitor else None
        if not workspace_id and current_snapshot.scan_run_id:
            scan_run = (
                self.db.query(ScanRun)
                .filter(ScanRun.id == current_snapshot.scan_run_id)
                .first()
            )
            if scan_run:
                workspace_id = scan_run.workspace_id

        if not workspace_id:
            logger.warning(
                f"Unable to resolve workspace_id for snapshot {current_snapshot.id}"
            )
            return None

        # 7. Create and persist Change record
        change = Change(
            workspace_id=workspace_id,
            competitor_id=competitor_id,
            source_id=current_snapshot.source_id,
            scan_run_id=current_snapshot.scan_run_id,
            previous_snapshot_id=prior_snapshot.id,
            current_snapshot_id=current_snapshot.id,
            change_hash=diff_result.change_hash,
            change_type=diff_result.change_type,
            category=classification.category,
            is_meaningful=classification.is_meaningful,
            significance_score=classification.significance_score,
            summary=classification.summary,
            diff_unified=diff_result.diff_unified,
            diff_stats=diff_result.diff_stats,
            detected_at=datetime.now(timezone.utc),
        )
        self.db.add(change)
        self.db.flush()
        return change

    def detect_changes_for_scan_run(self, scan_run_id: str) -> List[Change]:
        """
        Run change detection across all successful snapshots of a scan run.
        """
        snapshots = (
            self.db.query(Snapshot)
            .filter(
                Snapshot.scan_run_id == scan_run_id,
                Snapshot.status == "success",
            )
            .all()
        )
        changes: List[Change] = []
        for snapshot in snapshots:
            change = self.detect_change_for_snapshot(snapshot)
            if change:
                changes.append(change)
        return changes
