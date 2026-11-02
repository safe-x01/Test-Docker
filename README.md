# SAFE-X mock stack — DB dictionary aligned + EMQX

This local test stack aligns its PostgreSQL schema to `safealert_database_data_dictionary(2).json` and keeps the existing mock flow:

`esp32-mock -> EMQX -> deepcraft-adapter -> backend -> PostgreSQL -> notifier`

## Important alignment choices

- The old demo tables `incidents` and `sensor_events` are replaced by the supplied logical DB schema.
- MQTT uses human-readable `device_code` and `zone_code`; backend resolves them to DB UUIDs.
- Every adapter message is stored in `SENSOR_READING.payload`.
- `PRE_FIRE` / `FIRE` additionally create `INCIDENT`, `INCIDENT_SOURCE`, `AI_ANALYSIS`, and `NOTIFICATION`.
- `NORMAL` creates only `SENSOR_READING` and updates `DEVICE.last_seen_at`.
- `SENSOR_READING.zone_id`, `CAMERA_DETECTION.zone_id`, and `INCIDENT_SOURCE.reading_ref` remain non-FK because the supplied dictionary explicitly does not mark them as FK fields.
- Both `SENSOR_READING.id` and `recorded_at` are implemented as a composite primary key because both are marked PK in the supplied dictionary. This should still be confirmed with the DB/ER owner.
- The dictionary does not define nullability, defaults, string lengths, numeric precision, or enum allowed values. This demo deliberately avoids inventing those DB constraints.
- Demo status strings such as `DETECTED`, `PENDING`, `DELIVERED`, `RETRY`, and `FAILED` are application conventions only, not enums from the supplied DB.

## Demo seed

The one-shot `seed` container creates:

- Floor 1
- Zone `room-a1`
- Device `esp32-node-01`

These values are mock data only.

## Run

If upgrading from the old demo schema, this migration drops the old mock tables. Back up anything you care about first.

```bash
docker compose --profile dev --profile mock up --build -d
```

Check:

```bash
docker compose --profile dev --profile mock ps -a
docker compose logs -f esp32-mock deepcraft-adapter backend notifier
```

Open:

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Adminer: http://localhost:8081
- EMQX Dashboard: http://localhost:18183

EMQX Dashboard default login for a fresh install is normally `admin` / `public`; change it when prompted.

## Test data flow

`esp32-mock` cycles through `NORMAL -> PRE_FIRE -> FIRE` every 5 seconds.

Expected DB behavior:

- NORMAL: insert `SENSOR_READING`
- PRE_FIRE/FIRE: insert `SENSOR_READING`, `INCIDENT`, `INCIDENT_SOURCE`, `AI_ANALYSIS`, `NOTIFICATION`
- notifier: sends simulated Telegram when dummy credentials are used, then updates `NOTIFICATION.status`
