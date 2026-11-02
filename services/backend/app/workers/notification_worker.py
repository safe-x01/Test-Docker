import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Incident, Notification


def send_notification(incident: Incident) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "dummy")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "dummy")
    text = f"[Incident {incident.id}] type={incident.incident_type} severity={incident.severity}"

    if token == "dummy" or chat_id == "dummy":
        print(f"[SIMULATED TELEGRAM] {text}", flush=True)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    with urllib.request.urlopen(url, data=body, timeout=10) as response:
        print(f"Telegram status: {response.status}", flush=True)


def main() -> None:
    print("Notification worker started", flush=True)
    while True:
        try:
            with SessionLocal() as db:
                rows = db.execute(
                    select(Notification, Incident)
                    .join(Incident, Incident.id == Notification.incident_id)
                    .where(Notification.status.in_(["PENDING", "RETRY"]))
                    .order_by(Notification.triggered_at.asc())
                    .limit(50)
                ).all()

                for notification, incident in rows:
                    try:
                        send_notification(incident)
                        notification.status = "DELIVERED"
                        notification.delivered_at = datetime.now(timezone.utc)
                    except Exception as exc:
                        notification.retry_count = (notification.retry_count or 0) + 1
                        notification.status = "FAILED" if notification.retry_count >= 3 else "RETRY"
                        print(f"Notification error id={notification.id}: {exc}", flush=True)
                db.commit()
        except Exception as exc:
            print(f"Worker error: {exc}", flush=True)

        time.sleep(5)


if __name__ == "__main__":
    main()
