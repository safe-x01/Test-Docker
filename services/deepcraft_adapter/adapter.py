import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "emqx")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
RAW_TOPIC = os.getenv("RAW_TOPIC", "safe-x/v1/nodes/+/telemetry")
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "safe-x/v1/adapter/events")
PRE_FIRE_THRESHOLD = float(os.getenv("PRE_FIRE_THRESHOLD", "0.55"))
FIRE_THRESHOLD = float(os.getenv("FIRE_THRESHOLD", "0.80"))

VALID_LABELS = {"NORMAL", "PRE_FIRE", "FIRE"}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def as_float(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def validate_and_normalize(raw: dict[str, Any], source_topic: str) -> dict[str, Any]:
    """SAFE-X demo MQTT contract; not an official DEEPCRAFT wire protocol."""
    device_code = str(raw.get("device_code") or raw.get("node_id") or "").strip()
    if not device_code:
        raise ValueError("device_code is required")

    sensors = raw.get("sensors") or {}
    inference = raw.get("inference") or {}
    location = raw.get("location") or {}

    temperature_c = as_float(sensors.get("temperature_c"), "sensors.temperature_c")
    smoke = clamp(as_float(sensors.get("smoke", 0.0), "sensors.smoke"))
    gas_ppm = max(0.0, as_float(sensors.get("gas_ppm", 0.0), "sensors.gas_ppm"))
    humidity_pct = clamp(as_float(sensors.get("humidity_pct", 0.0), "sensors.humidity_pct"), 0.0, 100.0)
    flame = bool(sensors.get("flame", False))

    label = str(inference.get("label", "NORMAL")).upper().strip()
    if label not in VALID_LABELS:
        raise ValueError(f"unsupported inference label: {label}")

    confidence = clamp(as_float(inference.get("confidence", 0.0), "inference.confidence"))
    scores = inference.get("scores") or {}
    normal_score = clamp(as_float(scores.get("NORMAL", 0.0), "scores.NORMAL"))
    pre_fire_score = clamp(as_float(scores.get("PRE_FIRE", 0.0), "scores.PRE_FIRE"))
    fire_score = clamp(as_float(scores.get("FIRE", 0.0), "scores.FIRE"))

    if normal_score + pre_fire_score + fire_score <= 0:
        normal_score = confidence if label == "NORMAL" else 0.0
        pre_fire_score = confidence if label == "PRE_FIRE" else 0.0
        fire_score = confidence if label == "FIRE" else 0.0

    # Demo-only fusion logic. These weights are not taken from DEEPCRAFT or the DB schema.
    model_risk = clamp(fire_score + 0.50 * pre_fire_score)
    temperature_risk = clamp((temperature_c - 35.0) / 45.0)
    gas_risk = clamp(gas_ppm / 700.0)
    flame_risk = 1.0 if flame else 0.0
    risk_score = clamp(
        0.60 * model_risk
        + 0.15 * temperature_risk
        + 0.10 * smoke
        + 0.05 * gas_risk
        + 0.10 * flame_risk
    )

    if risk_score >= FIRE_THRESHOLD or (label == "FIRE" and confidence >= 0.70):
        decision, risk_level = "FIRE", "critical"
    elif risk_score >= PRE_FIRE_THRESHOLD or (label == "PRE_FIRE" and confidence >= 0.60):
        decision, risk_level = "PRE_FIRE", "high"
    elif risk_score >= 0.35:
        decision, risk_level = "NORMAL", "medium"
    else:
        decision, risk_level = "NORMAL", "low"

    zone_code = str(location.get("zone_code") or location.get("zone_id") or "unknown")
    model_version = str(
        inference.get("model_version")
        or inference.get("model")
        or "unknown"
    )

    return {
        "schema_version": 2,
        "event_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "raw_timestamp": raw.get("timestamp"),
        "source_topic": source_topic,
        "device_code": device_code,
        "zone_code": zone_code,
        "model": {
            "model_version": model_version,
            "label": label,
            "confidence": round(confidence, 4),
            "scores": {
                "NORMAL": round(normal_score, 4),
                "PRE_FIRE": round(pre_fire_score, 4),
                "FIRE": round(fire_score, 4),
            },
        },
        "sensors": {
            "temperature_c": round(temperature_c, 2),
            "smoke": round(smoke, 4),
            "gas_ppm": round(gas_ppm, 2),
            "flame": flame,
            "humidity_pct": round(humidity_pct, 2),
        },
        "adapter": {
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "decision": decision,
            "algorithm": "safe-x-demo-fusion-v2",
        },
    }


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connected to MQTT; subscribing to {RAW_TOPIC}", flush=True)
        client.subscribe(RAW_TOPIC, qos=1)
    else:
        print(f"MQTT connection failed: {reason_code}", flush=True)


def on_message(client, userdata, message):
    try:
        raw = json.loads(message.payload.decode("utf-8"))
        normalized = validate_and_normalize(raw, message.topic)
        info = client.publish(OUTPUT_TOPIC, json.dumps(normalized, separators=(",", ":")), qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"publish failed rc={info.rc}")
        print(
            "adapter event "
            f"device={normalized['device_code']} "
            f"model={normalized['model']['label']} "
            f"decision={normalized['adapter']['decision']} "
            f"risk={normalized['adapter']['risk_score']}",
            flush=True,
        )
    except Exception as exc:
        print(f"Rejected MQTT message topic={message.topic}: {exc}", flush=True)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="safe-x-deepcraft-adapter")
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            print(f"Connecting to MQTT at {MQTT_HOST}:{MQTT_PORT}", flush=True)
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_forever()
        except Exception as exc:
            print(f"MQTT adapter error: {exc}; retrying in 3s", flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main()
