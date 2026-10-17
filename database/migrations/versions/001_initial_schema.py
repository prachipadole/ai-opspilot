"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Incidents ─────────────────────────────────────────────────────────────
    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('raw_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_incidents_status', 'incidents', ['status'])
    op.create_index('idx_incidents_severity', 'incidents', ['severity'])

    # ── Anomalies ──────────────────────────────────────────────────────────────
    op.create_table(
        'anomalies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metric_name', sa.Text(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('anomaly_score', sa.Float(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_acknowledged', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.create_index('idx_anomalies_detected', 'anomalies', ['detected_at'])

    # ── Analyses ───────────────────────────────────────────────────────────────
    op.create_table(
        'analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('runbooks_used', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('llm_model', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Remediations ───────────────────────────────────────────────────────────
    op.create_table(
        'remediations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_name', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('approved_by', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Log Entries ───────────────────────────────────────────────────────────
    op.create_table(
        'log_entries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('service', sa.Text(), nullable=True),
        sa.Column('level', sa.String(length=10), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
    )
    op.create_index('idx_log_entries_time', 'log_entries', ['timestamp'])


def downgrade() -> None:
    op.drop_table('log_entries')
    op.drop_table('remediations')
    op.drop_table('analyses')
    op.drop_table('anomalies')
    op.drop_table('incidents')
