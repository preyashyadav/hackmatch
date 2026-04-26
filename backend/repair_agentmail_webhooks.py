from urllib.parse import urljoin

import config
from db import SessionLocal
from models import Attendee
from services.agentmail_service import ensure_webhook_registration


def main() -> None:
    if not config.WEBHOOK_BASE_URL:
        raise RuntimeError("WEBHOOK_BASE_URL is not configured.")

    webhook_url = urljoin(config.WEBHOOK_BASE_URL.rstrip("/") + "/", "webhook/agentmail")
    session = SessionLocal()
    try:
        attendees = session.query(Attendee).all()
        print(f"Checking webhook registrations for {len(attendees)} attendees...")
        for attendee in attendees:
            webhook_id = ensure_webhook_registration(attendee.inbox_id, webhook_url)
            print(f"{attendee.name} ({attendee.agent_email}) -> webhook {webhook_id}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
