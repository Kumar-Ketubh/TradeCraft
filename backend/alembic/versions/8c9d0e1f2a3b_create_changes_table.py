"""create changes table

Revision ID: 8c9d0e1f2a3b
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-11 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c9d0e1f2a3b'
down_revision: Union[str, Sequence[str], None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'changes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('competitor_id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('scan_run_id', sa.String(length=36), nullable=False),
        sa.Column('previous_snapshot_id', sa.String(length=36), nullable=True),
        sa.Column('current_snapshot_id', sa.String(length=36), nullable=False),
        sa.Column('change_hash', sa.String(length=64), nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('is_meaningful', sa.Boolean(), nullable=False),
        sa.Column('significance_score', sa.Float(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('diff_unified', sa.Text(), nullable=False),
        sa.Column('diff_stats', sa.JSON(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['current_snapshot_id'], ['snapshots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['previous_snapshot_id'], ['snapshots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scan_run_id'], ['scan_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_changes_category'), 'changes', ['category'], unique=False)
    op.create_index(op.f('ix_changes_change_hash'), 'changes', ['change_hash'], unique=False)
    op.create_index(op.f('ix_changes_change_type'), 'changes', ['change_type'], unique=False)
    op.create_index(op.f('ix_changes_competitor_id'), 'changes', ['competitor_id'], unique=False)
    op.create_index(op.f('ix_changes_current_snapshot_id'), 'changes', ['current_snapshot_id'], unique=False)
    op.create_index(op.f('ix_changes_detected_at'), 'changes', ['detected_at'], unique=False)
    op.create_index(op.f('ix_changes_is_meaningful'), 'changes', ['is_meaningful'], unique=False)
    op.create_index(op.f('ix_changes_previous_snapshot_id'), 'changes', ['previous_snapshot_id'], unique=False)
    op.create_index(op.f('ix_changes_scan_run_id'), 'changes', ['scan_run_id'], unique=False)
    op.create_index(op.f('ix_changes_source_id'), 'changes', ['source_id'], unique=False)
    op.create_index(op.f('ix_changes_workspace_id'), 'changes', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_changes_workspace_id'), table_name='changes')
    op.drop_index(op.f('ix_changes_source_id'), table_name='changes')
    op.drop_index(op.f('ix_changes_scan_run_id'), table_name='changes')
    op.drop_index(op.f('ix_changes_previous_snapshot_id'), table_name='changes')
    op.drop_index(op.f('ix_changes_is_meaningful'), table_name='changes')
    op.drop_index(op.f('ix_changes_detected_at'), table_name='changes')
    op.drop_index(op.f('ix_changes_current_snapshot_id'), table_name='changes')
    op.drop_index(op.f('ix_changes_competitor_id'), table_name='changes')
    op.drop_index(op.f('ix_changes_change_type'), table_name='changes')
    op.drop_index(op.f('ix_changes_change_hash'), table_name='changes')
    op.drop_index(op.f('ix_changes_category'), table_name='changes')
    op.drop_table('changes')
