from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Floor(Base):
    __tablename__ = "FLOOR"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    floor_number: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String)
    floorplan_path: Mapped[str | None] = mapped_column(String)


class Zone(Base):
    __tablename__ = "ZONE"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    floor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("FLOOR.id"))
    zone_code: Mapped[str | None] = mapped_column(String, unique=True)
    zone_type: Mapped[str | None] = mapped_column(String)
    is_evacuation_route: Mapped[bool | None] = mapped_column(Boolean)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Device(Base):
    __tablename__ = "DEVICE"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ZONE.id"))
    device_code: Mapped[str | None] = mapped_column(String, unique=True)
    device_kind: Mapped[str | None] = mapped_column(String)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric)
    is_active: Mapped[bool | None] = mapped_column(Boolean)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Beacon(Base):
    __tablename__ = "BEACON"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ZONE.id"))
    beacon_uid: Mapped[str | None] = mapped_column(String, unique=True)
    tx_power: Mapped[int | None] = mapped_column(Integer)
    pos_x: Mapped[Decimal | None] = mapped_column(Numeric)
    pos_y: Mapped[Decimal | None] = mapped_column(Numeric)


class AppUser(Base):
    __tablename__ = "APP_USER"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    employee_code: Mapped[str | None] = mapped_column(String, unique=True)
    display_name: Mapped[str | None] = mapped_column(String)
    role: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool | None] = mapped_column(Boolean)
    current_zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ZONE.id"))
    floor_number: Mapped[int | None] = mapped_column(Integer)
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric)
    location_method: Mapped[str | None] = mapped_column(String)
    location_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserDevice(Base):
    __tablename__ = "USER_DEVICE"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("APP_USER.id"))
    install_id: Mapped[str | None] = mapped_column(String, unique=True)
    fcm_token: Mapped[str | None] = mapped_column(String)
    platform: Mapped[str | None] = mapped_column(String)
    last_sync_seq: Mapped[int | None] = mapped_column(BigInteger)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SensorReading(Base):
    __tablename__ = "SENSOR_READING"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("DEVICE.id"))
    # Intentionally not an FK: the supplied ER dictionary does not mark it as one.
    zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    raw_value: Mapped[Decimal | None] = mapped_column(Numeric)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_alarm: Mapped[bool | None] = mapped_column(Boolean)


class CameraDetection(Base):
    __tablename__ = "CAMERA_DETECTION"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("DEVICE.id"))
    # Intentionally not an FK: the supplied ER dictionary does not mark it as one.
    zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    detection_class: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric)
    bbox: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    frame_path: Mapped[str | None] = mapped_column(String)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Incident(Base):
    __tablename__ = "INCIDENT"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ZONE.id"))
    verified_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("APP_USER.id"))
    incident_type: Mapped[str | None] = mapped_column(String)
    severity: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric)
    source_count: Mapped[int | None] = mapped_column(Integer)
    camera_verified: Mapped[bool | None] = mapped_column(Boolean)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seq: Mapped[int | None] = mapped_column(BigInteger)


class IncidentSource(Base):
    __tablename__ = "INCIDENT_SOURCE"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("INCIDENT.id"))
    device_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("DEVICE.id"))
    source_kind: Mapped[str | None] = mapped_column(String)
    # Intentionally not an FK: the supplied ER dictionary does not mark it as one.
    reading_ref: Mapped[int | None] = mapped_column(BigInteger)
    value_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    weight: Mapped[Decimal | None] = mapped_column(Numeric)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIAnalysis(Base):
    __tablename__ = "AI_ANALYSIS"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    incident_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("INCIDENT.id"))
    model_version: Mapped[str | None] = mapped_column(String)
    anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric)
    event_class: Mapped[str | None] = mapped_column(String)
    severity_score: Mapped[Decimal | None] = mapped_column(Numeric)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric)
    fusion_stage: Mapped[str | None] = mapped_column(String)
    feature_vector: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentEvidence(Base):
    __tablename__ = "INCIDENT_EVIDENCE"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("INCIDENT.id"))
    media_kind: Mapped[str | None] = mapped_column(String)
    local_path: Mapped[str | None] = mapped_column(String)
    is_exportable: Mapped[bool | None] = mapped_column(Boolean)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Report(Base):
    __tablename__ = "REPORT"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    client_uuid: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), unique=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("APP_USER.id"))
    incident_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("INCIDENT.id"))
    zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ZONE.id"))
    report_type: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    attachment_count: Mapped[int | None] = mapped_column(Integer)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seq: Mapped[int | None] = mapped_column(BigInteger)


class Acknowledgement(Base):
    __tablename__ = "ACKNOWLEDGEMENT"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    client_uuid: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), unique=True)
    incident_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("INCIDENT.id"))
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("APP_USER.id"))
    zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ZONE.id"))
    ack_status: Mapped[str | None] = mapped_column(String)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_time_sec: Mapped[int | None] = mapped_column(Integer)


class Notification(Base):
    __tablename__ = "NOTIFICATION"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    incident_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("INCIDENT.id"))
    channel: Mapped[str | None] = mapped_column(String)
    recipient_type: Mapped[str | None] = mapped_column(String)
    priority: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    retry_count: Mapped[int | None] = mapped_column(Integer)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
