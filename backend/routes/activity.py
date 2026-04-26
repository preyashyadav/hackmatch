import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from db import get_db
from models import Attendee, Match
from services.matching import make_preview


router = APIRouter()


def _conversation_id(match_id: str, timestamp: str, message_id: str) -> str:
    return hashlib.sha1(f"{match_id}:{timestamp}:{message_id}".encode("utf-8")).hexdigest()[:16]


def _recipient_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("/attendees/{attendee_id}/activity")
def get_activity(attendee_id: str, db: Session = Depends(get_db)) -> list[dict]:
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")

    matches = (
        db.query(Match)
        .filter(or_(Match.attendee_a_id == attendee_id, Match.attendee_b_id == attendee_id))
        .all()
    )

    activity: list[dict] = []
    for match in matches:
        try:
            conversation = json.loads(match.agent_conversation or "[]")
        except json.JSONDecodeError:
            conversation = []

        for item in conversation:
            from_email = str(item.get("from_email", ""))
            to_email = str(item.get("to_email", ""))
            recipients = _recipient_list(to_email)
            if from_email == attendee.agent_email:
                direction = "outgoing"
            elif attendee.agent_email in recipients or attendee.contact_email in recipients:
                direction = "incoming"
            else:
                continue

            timestamp = str(item.get("timestamp", ""))
            full_body = str(item.get("full_body", ""))
            message_id = str(item.get("message_id", ""))
            activity.append(
                {
                    "conversation_id": _conversation_id(match.id, timestamp, message_id),
                    "match_id": match.id,
                    "from_email": from_email,
                    "to_email": to_email,
                    "from_name": str(item.get("from_name", "")),
                    "to_name": str(item.get("to_name", "")),
                    "direction": direction,
                    "preview": str(item.get("preview", "")) or make_preview(full_body),
                    "full_body": full_body,
                    "timestamp": timestamp,
                    "meta": item.get("meta", {}),
                }
            )

    activity.sort(key=lambda item: item["timestamp"], reverse=True)
    return activity
