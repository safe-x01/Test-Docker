"""replace demo tables with SafeAlert ER dictionary schema

Revision ID: 0003
Revises: 0002

The supplied dictionary defines field names/types and PK/FK/UQ flags but not
nullability/defaults/enums. Non-PK columns are therefore left nullable unless a
constraint is explicitly described by PK/FK/UQ metadata.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("sensor_events")
    op.drop_table("incidents")

    op.create_table(
        "FLOOR",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("floor_number", sa.Integer()),
        sa.Column("label", sa.String()),
        sa.Column("floorplan_path", sa.String()),
    )

    op.create_table(
        "ZONE",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("floor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("FLOOR.id")),
        sa.Column("zone_code", sa.String(), unique=True),
        sa.Column("zone_type", sa.String()),
        sa.Column("is_evacuation_route", sa.Boolean()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "DEVICE",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ZONE.id")),
        sa.Column("device_code", sa.String(), unique=True),
        sa.Column("device_kind", sa.String()),
        sa.Column("threshold_value", sa.Numeric()),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "BEACON",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ZONE.id")),
        sa.Column("beacon_uid", sa.String(), unique=True),
        sa.Column("tx_power", sa.Integer()),
        sa.Column("pos_x", sa.Numeric()),
        sa.Column("pos_y", sa.Numeric()),
    )

    op.create_table(
        "APP_USER",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_code", sa.String(), unique=True),
        sa.Column("display_name", sa.String()),
        sa.Column("role", sa.String()),
        sa.Column("email", sa.String(), unique=True),
        sa.Column("password_hash", sa.String()),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("current_zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ZONE.id")),
        sa.Column("floor_number", sa.Integer()),
        sa.Column("accuracy_m", sa.Numeric()),
        sa.Column("location_method", sa.String()),
        sa.Column("location_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "USER_DEVICE",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("APP_USER.id")),
        sa.Column("install_id", sa.String(), unique=True),
        sa.Column("fcm_token", sa.String()),
        sa.Column("platform", sa.String()),
        sa.Column("last_sync_seq", sa.BigInteger()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "SENSOR_READING",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("DEVICE.id")),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("raw_value", sa.Numeric()),
        sa.Column("normalized_value", sa.Numeric()),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("is_alarm", sa.Boolean()),
    )

    op.create_table(
        "CAMERA_DETECTION",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("DEVICE.id")),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True)),
        sa.Column("detection_class", sa.String()),
        sa.Column("confidence", sa.Numeric()),
        sa.Column("bbox", postgresql.ARRAY(sa.Integer())),
        sa.Column("frame_path", sa.String()),
        sa.Column("detected_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "INCIDENT",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ZONE.id")),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("APP_USER.id")),
        sa.Column("incident_type", sa.String()),
        sa.Column("severity", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("confidence_score", sa.Numeric()),
        sa.Column("source_count", sa.Integer()),
        sa.Column("camera_verified", sa.Boolean()),
        sa.Column("detected_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("seq", sa.BigInteger()),
    )

    op.create_table(
        "INCIDENT_SOURCE",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("INCIDENT.id")),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("DEVICE.id")),
        sa.Column("source_kind", sa.String()),
        sa.Column("reading_ref", sa.BigInteger()),
        sa.Column("value_snapshot", postgresql.JSONB()),
        sa.Column("weight", sa.Numeric()),
        sa.Column("linked_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "AI_ANALYSIS",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("INCIDENT.id")),
        sa.Column("model_version", sa.String()),
        sa.Column("anomaly_score", sa.Numeric()),
        sa.Column("event_class", sa.String()),
        sa.Column("severity_score", sa.Numeric()),
        sa.Column("confidence", sa.Numeric()),
        sa.Column("fusion_stage", sa.String()),
        sa.Column("feature_vector", postgresql.JSONB()),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "INCIDENT_EVIDENCE",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("INCIDENT.id")),
        sa.Column("media_kind", sa.String()),
        sa.Column("local_path", sa.String()),
        sa.Column("is_exportable", sa.Boolean()),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "REPORT",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_uuid", postgresql.UUID(as_uuid=True), unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("APP_USER.id")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("INCIDENT.id")),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ZONE.id")),
        sa.Column("report_type", sa.String()),
        sa.Column("description", sa.String()),
        sa.Column("attachment_count", sa.Integer()),
        sa.Column("reported_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("seq", sa.BigInteger()),
    )

    op.create_table(
        "ACKNOWLEDGEMENT",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_uuid", postgresql.UUID(as_uuid=True), unique=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("INCIDENT.id")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("APP_USER.id")),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ZONE.id")),
        sa.Column("ack_status", sa.String()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("response_time_sec", sa.Integer()),
    )

    op.create_table(
        "NOTIFICATION",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("INCIDENT.id")),
        sa.Column("channel", sa.String()),
        sa.Column("recipient_type", sa.String()),
        sa.Column("priority", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("retry_count", sa.Integer()),
        sa.Column("triggered_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )

    op.create_index("ix_sensor_reading_device_recorded", "SENSOR_READING", ["device_id", "recorded_at"])
    op.create_index("ix_incident_detected_at", "INCIDENT", ["detected_at"])
    op.create_index("ix_notification_status", "NOTIFICATION", ["status"])


def downgrade():
    op.drop_index("ix_notification_status", table_name="NOTIFICATION")
    op.drop_index("ix_incident_detected_at", table_name="INCIDENT")
    op.drop_index("ix_sensor_reading_device_recorded", table_name="SENSOR_READING")

    for table in [
        "NOTIFICATION",
        "ACKNOWLEDGEMENT",
        "REPORT",
        "INCIDENT_EVIDENCE",
        "AI_ANALYSIS",
        "INCIDENT_SOURCE",
        "INCIDENT",
        "CAMERA_DETECTION",
        "SENSOR_READING",
        "USER_DEVICE",
        "APP_USER",
        "BEACON",
        "DEVICE",
        "ZONE",
        "FLOOR",
    ]:
        op.drop_table(table)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
