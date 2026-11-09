"""add report attachments and storage path

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    # Align INCIDENT_EVIDENCE with the updated SAFE-X Data Dictionary.
    # Rename rather than drop/add so existing path values are preserved.
    op.alter_column(
        "INCIDENT_EVIDENCE",
        "local_path",
        new_column_name="storage_path",
    )

    # Attachment metadata for files associated with Mobile Reports.
    op.create_table(
        "REPORT_ATTACHMENT",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("REPORT.id"),
        ),
        sa.Column("media_kind", sa.String()),
        sa.Column("storage_path", sa.String()),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table("REPORT_ATTACHMENT")

    op.alter_column(
        "INCIDENT_EVIDENCE",
        "storage_path",
        new_column_name="local_path",
    )