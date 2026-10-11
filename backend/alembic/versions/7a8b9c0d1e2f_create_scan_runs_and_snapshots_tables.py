"""create scan_runs and snapshots tables

Revision ID: 7a8b9c0d1e2f
Revises: 5110aac07da3
Create Date: 2026-10-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = '5110aac07da3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'scan_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('competitor_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_sources', sa.Integer(), nullable=False),
        sa.Column('successful_sources', sa.Integer(), nullable=False),
        sa.Column('failed_sources', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scan_runs_competitor_id'), 'scan_runs', ['competitor_id'], unique=False)
    op.create_index(op.f('ix_scan_runs_created_at'), 'scan_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_scan_runs_status'), 'scan_runs', ['status'], unique=False)
    op.create_index(op.f('ix_scan_runs_workspace_id'), 'scan_runs', ['workspace_id'], unique=False)

    op.create_table(
        'snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('scan_run_id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('normalized_content', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['scan_run_id'], ['scan_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_snapshots_content_hash'), 'snapshots', ['content_hash'], unique=False)
    op.create_index(op.f('ix_snapshots_created_at'), 'snapshots', ['created_at'], unique=False)
    op.create_index(op.f('ix_snapshots_scan_run_id'), 'snapshots', ['scan_run_id'], unique=False)
    op.create_index(op.f('ix_snapshots_source_id'), 'snapshots', ['source_id'], unique=False)
    op.create_index(op.f('ix_snapshots_status'), 'snapshots', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_snapshots_status'), table_name='snapshots')
    op.drop_index(op.f('ix_snapshots_source_id'), table_name='snapshots')
    op.drop_index(op.f('ix_snapshots_scan_run_id'), table_name='snapshots')
    op.drop_index(op.f('ix_snapshots_created_at'), table_name='snapshots')
    op.drop_index(op.f('ix_snapshots_content_hash'), table_name='snapshots')
    op.drop_table('snapshots')

    op.drop_index(op.f('ix_scan_runs_workspace_id'), table_name='scan_runs')
    op.drop_index(op.f('ix_scan_runs_status'), table_name='scan_runs')
    op.drop_index(op.f('ix_scan_runs_created_at'), table_name='scan_runs')
    op.drop_index(op.f('ix_scan_runs_competitor_id'), table_name='scan_runs')
    op.drop_table('scan_runs')
