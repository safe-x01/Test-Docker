import json
import os
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


MQTT_HOST = os.getenv("MQTT_HOST", "emqx")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

DEVICE_CODE = os.getenv("DEVICE_CODE", "esp32-node-01")
ZONE_CODE = os.getenv("ZONE_CODE", "room-a1")

MODEL_VERSION = os.getenv(
    "MODEL_VERSION",
    "deepcraft-fire-demo-v1",
)

PUBLISH_TOPIC = os.getenv(
    "PUBLISH_TOPIC",
    f"safe-x/v1/nodes/{DEVICE_CODE}/telemetry",
)

INTERVAL = float(
    os.getenv("MOCK_INTERVAL_SECONDS", "20")
)

SCENARIO_MODE = os.getenv(
    "MOCK_SCENARIO",
    "cycle",
).lower()


SCENARIOS = {
    "normal": {
        "sensors": {
            "temperature_c": 27.4,
            "smoke": 0.03,
            "gas_ppm": 82,
            "flame": False,
            "humidity_pct": 56.0,
        },
        "inference": {
            "label": "NORMAL",
            "confidence": 0.96,
            "scores": {
                "NORMAL": 0.96,
                "PRE_FIRE": 0.03,
                "FIRE": 0.01,
            },
        },
    },

    "pre_fire": {
        "sensors": {
            "temperature_c": 51.0,
            "smoke": 0.58,
            "gas_ppm": 340,
            "flame": False,
            "humidity_pct": 42.0,
        },
        "inference": {
            "label": "PRE_FIRE",
            "confidence": 0.77,
            "scores": {
                "NORMAL": 0.08,
                "PRE_FIRE": 0.77,
                "FIRE": 0.15,
            },
        },
    },

    "fire": {
        "sensors": {
            "temperature_c": 82.0,
            "smoke": 0.94,
            "gas_ppm": 680,
            "flame": True,
            "humidity_pct": 25.0,
        },
        "inference": {
            "label": "FIRE",
            "confidence": 0.93,
            "scores": {
                "NORMAL": 0.01,
                "PRE_FIRE": 0.06,
                "FIRE": 0.93,
            },
        },
    },
}


mqtt_connected = threading.Event()


def payload_for(name: str) -> dict:
    base = SCENARIOS[name]

    return {
        "schema_version": 2,

        "device_code": DEVICE_CODE,

        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "location": {
            "zone_code": ZONE_CODE
        },

        "sensors": base["sensors"],

        "inference": {
            "model_version": MODEL_VERSION,
            **base["inference"],
        },
    }


def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties,
):
    if reason_code == 0:

        print(
            f"Connected to EMQX at "
            f"{MQTT_HOST}:{MQTT_PORT}",
            flush=True,
        )

        mqtt_connected.set()

    else:
        print(
            f"MQTT connection failed: "
            f"{reason_code}",
            flush=True,
        )


def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties,
):
    mqtt_connected.clear()

    print(
        f"Disconnected from MQTT: "
        f"{reason_code}",
        flush=True,
    )


def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"mock-{DEVICE_CODE}",
    )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    if MQTT_USERNAME:
        client.username_pw_set(
            MQTT_USERNAME,
            MQTT_PASSWORD,
        )

    client.reconnect_delay_set(
        min_delay=1,
        max_delay=10,
    )

    print(
        f"Connecting to EMQX "
        f"{MQTT_HOST}:{MQTT_PORT}...",
        flush=True,
    )

    client.connect(
        MQTT_HOST,
        MQTT_PORT,
        keepalive=60,
    )

    client.loop_start()

    # สำคัญ:
    # รอจน EMQX ตอบ CONNACK จริง
    if not mqtt_connected.wait(timeout=30):
        raise RuntimeError(
            "Could not establish MQTT connection "
            "within 30 seconds"
        )

    names = [
        "normal",
        "pre_fire",
        "fire",
    ]

    index = 0

    try:
        while True:

            # ถ้าหลุด ให้รอ reconnect
            mqtt_connected.wait()

            if SCENARIO_MODE == "cycle":

                scenario = names[
                    index % len(names)
                ]

                index += 1

            elif SCENARIO_MODE in SCENARIOS:
                scenario = SCENARIO_MODE

            else:
                raise ValueError(
                    "MOCK_SCENARIO must be "
                    "cycle, normal, pre_fire or fire"
                )

            payload = payload_for(
                scenario
            )

            info = client.publish(
                PUBLISH_TOPIC,
                json.dumps(payload),
                qos=1,
            )

            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                print(
                    f"Publish failed rc={info.rc}",
                    flush=True,
                )
                time.sleep(1)
                continue

            info.wait_for_publish(
                timeout=10
            )

            print(
                f"Published "
                f"scenario={scenario} "
                f"label={payload['inference']['label']} "
                f"topic={PUBLISH_TOPIC}",
                flush=True,
            )

            time.sleep(INTERVAL)

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()