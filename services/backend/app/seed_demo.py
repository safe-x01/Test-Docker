from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Device, Floor, Zone


FLOOR_ID = UUID("00000000-0000-0000-0000-000000000001")
ZONE_ID = UUID("00000000-0000-0000-0000-000000000002")
DEVICE_ID = UUID("00000000-0000-0000-0000-000000000003")


def main() -> None:
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:

        # ---------------------------------
        # 1. FLOOR
        # ---------------------------------

        floor = db.scalar(
            select(Floor).where(Floor.id == FLOOR_ID)
        )

        if floor is None:
            floor = Floor(
                id=FLOOR_ID,
                floor_number=1,
                label="Floor 1",
                floorplan_path=None,
            )

            db.add(floor)

            # สำคัญ:
            # ให้ INSERT FLOOR เข้า DB ก่อนสร้าง ZONE
            db.flush()

            print("Created demo FLOOR", flush=True)


        # ---------------------------------
        # 2. ZONE
        # ---------------------------------

        zone = db.scalar(
            select(Zone).where(Zone.id == ZONE_ID)
        )

        if zone is None:
            zone = Zone(
                id=ZONE_ID,
                floor_id=FLOOR_ID,
                zone_code="room-a1",
                zone_type="ROOM",
                is_evacuation_route=False,
                updated_at=now,
            )

            db.add(zone)

            # สำคัญ:
            # ให้ INSERT ZONE เข้า DB ก่อนสร้าง DEVICE
            db.flush()

            print("Created demo ZONE", flush=True)


        # ---------------------------------
        # 3. DEVICE
        # ---------------------------------

        device = db.scalar(
            select(Device).where(Device.id == DEVICE_ID)
        )

        if device is None:
            device = Device(
                id=DEVICE_ID,
                zone_id=ZONE_ID,
                device_code="esp32-node-01",
                device_kind="ESP32_DEEPCRAFT_NODE",
                threshold_value=Decimal("0.80"),
                is_active=True,
                last_seen_at=None,
            )

            db.add(device)

            db.flush()

            print("Created demo DEVICE", flush=True)


        # ---------------------------------
        # Commit
        # ---------------------------------

        db.commit()

        print(
            "Demo master data ready: "
            "floor=1 "
            "zone=room-a1 "
            "device=esp32-node-01",
            flush=True,
        )


if __name__ == "__main__":
    main()