"""create sensor_events table

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sensor_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("node_id", sa.String(length=100), nullable=False),
        sa.Column("zone_id", sa.String(length=100), nullable=False),
        sa.Column("source_topic", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=150), nullable=False),
        sa.Column("model_label", sa.String(length=30), nullable=False),
        sa.Column("model_confidence", sa.Float(), nullable=False),
        sa.Column("adapter_decision", sa.String(length=30), nullable=False),
        sa.Column("risk_level", sa.String(length=30), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_sensor_events_node_id", "sensor_events", ["node_id"])
    op.create_index("ix_sensor_events_created_at", "sensor_events", ["created_at"])


def downgrade():
    op.drop_index("ix_sensor_events_created_at", table_name="sensor_events")
    op.drop_index("ix_sensor_events_node_id", table_name="sensor_events")
    op.drop_table("sensor_events")
