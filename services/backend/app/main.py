import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text

from app.db import SessionLocal
from app.models import (
    AIAnalysis,
    Device,
    Incident,
    IncidentSource,
    Notification,
    SensorReading,
    Zone,
)

mqtt_connected = False
mqtt_client = None
ADAPTER_EVENT_TOPIC = os.getenv("ADAPTER_EVENT_TOPIC", "safe-x/v1/adapter/events")


def parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def dec(value, fallback: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(fallback)


def store_adapter_event(payload: dict) -> None:
    model = payload.get("model") or {}
    adapter = payload.get("adapter") or {}
    sensors = payload.get("sensors") or {}

    device_code = str(payload.get("device_code", "")).strip()
    zone_code = str(payload.get("zone_code", "")).strip()
    if not device_code or not zone_code:
        raise ValueError("device_code and zone_code are required")

    recorded_at = parse_dt(payload.get("raw_timestamp") or payload.get("received_at"))
    decision = str(adapter.get("decision", "NORMAL")).upper()
    risk_level = str(adapter.get("risk_level", "unknown"))
    risk_score = dec(adapter.get("risk_score", 0))
    model_confidence = dec(model.get("confidence", 0))

    with SessionLocal() as db:
        device = db.scalar(select(Device).where(Device.device_code == device_code))
        zone = db.scalar(select(Zone).where(Zone.zone_code == zone_code))
        if device is None:
            raise ValueError(f"unknown DEVICE.device_code: {device_code}")
        if zone is None:
            raise ValueError(f"unknown ZONE.zone_code: {zone_code}")
        if device.zone_id is not None and device.zone_id != zone.id:
            raise ValueError(f"device {device_code} is not assigned to zone {zone_code}")

        duplicate = db.scalar(
            select(SensorReading.id).where(
                SensorReading.device_id == device.id,
                SensorReading.recorded_at == recorded_at,
            )
        )
        if duplicate is not None:
            print(f"Duplicate reading ignored device={device_code} recorded_at={recorded_at.isoformat()}", flush=True)
            return

        device.last_seen_at = datetime.now(timezone.utc)

        reading = SensorReading(
            device_id=device.id,
            zone_id=zone.id,
            recorded_at=recorded_at,
            # The ER dictionary has one numeric raw/normalized pair while this demo node
            # emits multiple sensor channels. Preserve all channels in payload instead of
            # inventing a single canonical measurement.
            raw_value=None,
            normalized_value=None,
            payload=payload,
            is_alarm=decision in {"PRE_FIRE", "FIRE"},
        )
        db.add(reading)
        db.flush()

        if decision in {"PRE_FIRE", "FIRE"}:
            incident = Incident(
                id=uuid4(),
                zone_id=zone.id,
                verified_by=None,
                incident_type=decision,
                severity=risk_level,
                status="DETECTED",
                confidence_score=model_confidence,
                source_count=1,
                camera_verified=False,
                detected_at=recorded_at,
                confirmed_at=None,
                resolved_at=None,
                seq=None,
            )
            db.add(incident)
            db.flush()

            db.add(
                IncidentSource(
                    incident_id=incident.id,
                    device_id=device.id,
                    source_kind="SENSOR_AI",
                    reading_ref=reading.id,
                    value_snapshot=payload,
                    weight=Decimal("1.0"),
                    linked_at=datetime.now(timezone.utc),
                )
            )

            db.add(
                AIAnalysis(
                    id=uuid4(),
                    incident_id=incident.id,
                    model_version=str(model.get("model_version", "unknown")),
                    anomaly_score=risk_score,
                    event_class=decision,
                    severity_score=risk_score,
                    confidence=model_confidence,
                    fusion_stage="DEEPCRAFT_ADAPTER",
                    feature_vector={
                        "scores": model.get("scores") or {},
                        "sensors": sensors,
                        "adapter": adapter,
                    },
                    analyzed_at=datetime.now(timezone.utc),
                )
            )

            db.add(
                Notification(
                    id=uuid4(),
                    incident_id=incident.id,
                    channel="TELEGRAM",
                    recipient_type="OPERATOR",
                    priority=risk_level.upper(),
                    status="PENDING",
                    retry_count=0,
                    triggered_at=datetime.now(timezone.utc),
                    delivered_at=None,
                    read_at=None,
                )
            )

        db.commit()


def on_connect(client, userdata, flags, reason_code, properties):
    global mqtt_connected
    mqtt_connected = reason_code == 0
    print(f"MQTT connected: {mqtt_connected}; reason={reason_code}", flush=True)
    if mqtt_connected:
        client.subscribe(ADAPTER_EVENT_TOPIC, qos=1)
        print(f"Subscribed to adapter events: {ADAPTER_EVENT_TOPIC}", flush=True)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    global mqtt_connected
    mqtt_connected = False
    print(f"MQTT disconnected; reason={reason_code}", flush=True)


def on_message(client, userdata, message):
    if message.topic != ADAPTER_EVENT_TOPIC:
        return
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        store_adapter_event(payload)
        print(
            f"Stored adapter event={payload.get('event_id')} decision={(payload.get('adapter') or {}).get('decision')}",
            flush=True,
        )
    except Exception as exc:
        print(f"Invalid adapter event: {exc}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="safe-x-backend")
    username = os.getenv("MQTT_USERNAME", "")
    if username:
        client.username_pw_set(username, os.getenv("MQTT_PASSWORD", ""))
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect_async(
        os.environ.get("MQTT_HOST", "emqx"),
        int(os.environ.get("MQTT_PORT", "1883")),
        keepalive=60,
    )
    client.loop_start()
    mqtt_client = client
    yield
    client.loop_stop()
    client.disconnect()


app = FastAPI(title="SAFE-X Indoor Incident Demo API", version="0.3.0", lifespan=lifespan)


class IncidentCreate(BaseModel):
    zone_code: str
    incident_type: str
    severity: str
    confidence_score: float = 1.0


@app.get("/")
def root():
    return {
        "message": "SAFE-X Indoor Incident System is running",
        "docs": "/docs",
        "health": "/health",
        "devices": "/devices",
        "zones": "/zones",
        "sensor_readings": "/sensor-readings",
        "incidents": "/incidents",
    }


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "mqtt_connected": mqtt_connected, "adapter_event_topic": ADAPTER_EVENT_TOPIC}


@app.get("/zones")
def list_zones():
    with SessionLocal() as db:
        rows = db.scalars(select(Zone).order_by(Zone.zone_code.asc())).all()
    return [{"id": str(row.id), "zone_code": row.zone_code, "zone_type": row.zone_type, "floor_id": str(row.floor_id) if row.floor_id else None} for row in rows]


@app.get("/devices")
def list_devices():
    with SessionLocal() as db:
        rows = db.scalars(select(Device).order_by(Device.device_code.asc())).all()
    return [{"id": str(row.id), "device_code": row.device_code, "device_kind": row.device_kind, "zone_id": str(row.zone_id) if row.zone_id else None, "is_active": row.is_active, "last_seen_at": row.last_seen_at} for row in rows]


@app.get("/sensor-readings")
def list_sensor_readings(limit: int = 100):
    limit = max(1, min(limit, 500))
    with SessionLocal() as db:
        rows = db.scalars(select(SensorReading).order_by(SensorReading.recorded_at.desc()).limit(limit)).all()
    return [{"id": row.id, "device_id": str(row.device_id) if row.device_id else None, "zone_id": str(row.zone_id) if row.zone_id else None, "recorded_at": row.recorded_at, "is_alarm": row.is_alarm, "payload": row.payload} for row in rows]


@app.get("/incidents")
def list_incidents(limit: int = 100):
    limit = max(1, min(limit, 500))
    with SessionLocal() as db:
        rows = db.scalars(select(Incident).order_by(Incident.detected_at.desc()).limit(limit)).all()
    return [{"id": str(row.id), "zone_id": str(row.zone_id) if row.zone_id else None, "incident_type": row.incident_type, "severity": row.severity, "status": row.status, "confidence_score": float(row.confidence_score) if row.confidence_score is not None else None, "source_count": row.source_count, "detected_at": row.detected_at} for row in rows]


@app.post("/incidents")
def create_incident(payload: IncidentCreate):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        zone = db.scalar(select(Zone).where(Zone.zone_code == payload.zone_code))
        if zone is None:
            raise HTTPException(status_code=404, detail="zone_code not found")
        incident = Incident(
            id=uuid4(),
            zone_id=zone.id,
            verified_by=None,
            incident_type=payload.incident_type,
            severity=payload.severity,
            status="DETECTED",
            confidence_score=dec(payload.confidence_score),
            source_count=0,
            camera_verified=False,
            detected_at=now,
            confirmed_at=None,
            resolved_at=None,
            seq=None,
        )
        db.add(incident)
        db.add(Notification(id=uuid4(), incident_id=incident.id, channel="TELEGRAM", recipient_type="OPERATOR", priority=payload.severity.upper(), status="PENDING", retry_count=0, triggered_at=now, delivered_at=None, read_at=None))
        db.commit()
        db.refresh(incident)
    return {"id": str(incident.id), "zone_code": payload.zone_code, "incident_type": incident.incident_type, "severity": incident.severity, "status": incident.status, "detected_at": incident.detected_at}
