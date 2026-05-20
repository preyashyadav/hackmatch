import json
import logging
from datetime import datetime
from email.utils import parseaddr

from fastapi import APIRouter, BackgroundTasks

from db import SessionLocal
from models import Attendee, Match
from services.agent_reasoning import (
    compose_followup,
    compose_human_intro,
    compose_response,
    evaluate_followup,
    evaluate_proposal,
)
from services.agentmail_service import get_message, send_email
from services.matching import append_conversation_entry, build_synergy_data, get_proposer_and_receiver, make_preview
from utils.email_format import format_agent_email, parse_agent_email


logger = logging.getLogger(__name__)
router = APIRouter()

MAX_NEGOTIATION_ROUNDS = 2


def _first_email(value) -> str:
    if isinstance(value, list):
        return _first_email(value[0]) if value else ""
    if isinstance(value, dict):
        return (
            str(value.get("email") or value.get("address") or value.get("from") or "")
            .strip()
            .lower()
        )
    if isinstance(value, str):
        _, email_address = parseaddr(value.strip())
        return (email_address or value).strip().lower()
    return ""


def _load_match_participants(db, match_id: str) -> tuple[Match, Attendee, Attendee]:
    match = db.query(Match).filter(Match.id == match_id).first()
    if match is None:
        raise ValueError("Match not found")

    attendee_a = db.query(Attendee).filter(Attendee.id == match.attendee_a_id).first()
    attendee_b = db.query(Attendee).filter(Attendee.id == match.attendee_b_id).first()
    if attendee_a is None or attendee_b is None:
        raise ValueError("Match attendees not found")

    return match, attendee_a, attendee_b


def _unique_emails(*emails: str) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for email in emails:
        original = str(email).strip()
        normalized = original.lower()
        if not original or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(original)
    return deduped


def _resolve_body(message: dict) -> str:
    body = message.get("extracted_text") or message.get("text") or message.get("preview") or ""
    if body:
        return str(body)

    inbox_id = message.get("inbox_id")
    message_id = message.get("message_id")
    if not inbox_id or not message_id:
        return ""

    try:
        full_message = get_message(inbox_id=str(inbox_id), message_id=str(message_id))
    except Exception:
        logger.exception("Failed to fetch full AgentMail message %s for inbox %s", message_id, inbox_id)
        return ""

    return (
        getattr(full_message, "extracted_text", None)
        or getattr(full_message, "text", None)
        or getattr(full_message, "preview", None)
        or ""
    )


def _incoming_entry(
    *,
    sender: Attendee,
    recipient: Attendee,
    body: str,
    subject: str,
    timestamp: str,
    meta: dict,
    message_id: str,
    thread_id: str,
) -> dict:
    return {
        "from_email": sender.agent_email,
        "to_email": recipient.agent_email,
        "from_name": f"{sender.name}'s agent",
        "to_name": f"{recipient.name}'s agent",
        "direction": "incoming",
        "preview": make_preview(body),
        "full_body": body,
        "subject": subject,
        "timestamp": timestamp,
        "meta": meta,
        "message_id": message_id,
        "thread_id": thread_id,
    }


def _outgoing_entry(
    *,
    from_email: str,
    to_email: str,
    from_name: str,
    to_name: str,
    body: str,
    subject: str,
    timestamp: str,
    meta: dict,
    message_id: str | None = None,
    thread_id: str | None = None,
) -> dict:
    entry = {
        "from_email": from_email,
        "to_email": to_email,
        "from_name": from_name,
        "to_name": to_name,
        "direction": "outgoing",
        "preview": make_preview(body),
        "full_body": body,
        "subject": subject,
        "timestamp": timestamp,
        "meta": meta,
    }
    if message_id:
        entry["message_id"] = message_id
    if thread_id:
        entry["thread_id"] = thread_id
    return entry


def _has_purpose(match: Match, purpose: str) -> bool:
    try:
        conversation = match.agent_conversation or "[]"
        items = json.loads(conversation)
    except Exception:
        return False

    for item in items if isinstance(items, list) else []:
        meta = item.get("meta", {}) if isinstance(item, dict) else {}
        if str(meta.get("purpose", "")).strip() == purpose:
            return True
    return False


def _count_purpose(match: Match, purpose: str) -> int:
    try:
        conversation = match.agent_conversation or "[]"
        items = json.loads(conversation)
    except Exception:
        return 0

    count = 0
    for item in items if isinstance(items, list) else []:
        meta = item.get("meta", {}) if isinstance(item, dict) else {}
        if str(meta.get("purpose", "")).strip() == purpose:
            count += 1
    return count


def _process_match_proposal(
    db,
    *,
    match: Match,
    sender: Attendee,
    recipient: Attendee,
    subject: str,
    raw_body: str,
    plain_body: str,
    meta: dict,
    message_id: str,
    thread_id: str,
    timestamp: str,
) -> None:
    appended = append_conversation_entry(
        match,
        _incoming_entry(
            sender=sender,
            recipient=recipient,
            body=raw_body,
            subject=subject,
            timestamp=timestamp,
            meta=meta,
            message_id=message_id,
            thread_id=thread_id,
        ),
    )
    if not appended:
        logger.info("Proposal webhook message already recorded for match %s; continuing idempotent processing.", match.id)

    if match.status != "proposed":
        db.commit()
        return

    synergy_data = build_synergy_data(match)
    evaluation = evaluate_proposal(recipient, sender, plain_body, synergy_data)
    response_body = compose_response(
        match,
        evaluation["decision"],
        evaluation["reason"],
        sender,
        recipient,
        questions=evaluation.get("questions") or [],
    )
    response_meta = {
        "match_id": match.id,
        "purpose": "match_response",
        "decision": evaluation["decision"],
        "reason": evaluation["reason"],
        "questions": json.dumps(evaluation.get("questions") or []),
    }
    response_subject, response_full_body = format_agent_email(response_meta, response_body)
    response_message_id = send_email(
        from_inbox_id=recipient.inbox_id,
        to_email=sender.agent_email,
        subject=response_subject,
        body=response_full_body,
        in_reply_to=message_id,
    )
    append_conversation_entry(
        match,
        _outgoing_entry(
            from_email=recipient.agent_email,
            to_email=sender.agent_email,
            from_name=f"{recipient.name}'s agent",
            to_name=f"{sender.name}'s agent",
            body=response_full_body,
            subject=response_subject,
            timestamp=datetime.utcnow().isoformat(),
            meta=response_meta,
            message_id=response_message_id,
            thread_id=thread_id,
        ),
    )
    db.commit()


def _process_match_followup(
    db,
    *,
    match: Match,
    sender: Attendee,
    recipient: Attendee,
    subject: str,
    raw_body: str,
    plain_body: str,
    meta: dict,
    message_id: str,
    thread_id: str,
    timestamp: str,
) -> None:
    appended = append_conversation_entry(
        match,
        _incoming_entry(
            sender=sender,
            recipient=recipient,
            body=raw_body,
            subject=subject,
            timestamp=timestamp,
            meta=meta,
            message_id=message_id,
            thread_id=thread_id,
        ),
    )
    if not appended:
        logger.info("Followup webhook message already recorded for match %s; continuing idempotent processing.", match.id)

    if match.status in {"confirmed", "rejected", "met"}:
        db.commit()
        return

    synergy_data = build_synergy_data(match)
    evaluation = evaluate_followup(recipient, sender, plain_body, synergy_data)
    response_body = compose_response(match, evaluation["decision"], evaluation["reason"], sender, recipient)
    response_meta = {
        "match_id": match.id,
        "purpose": "match_response",
        "decision": evaluation["decision"],
        "reason": evaluation["reason"],
        "questions": "[]",
    }
    response_subject, response_full_body = format_agent_email(response_meta, response_body)
    response_message_id = send_email(
        from_inbox_id=recipient.inbox_id,
        to_email=sender.agent_email,
        subject=response_subject,
        body=response_full_body,
        in_reply_to=message_id,
    )
    append_conversation_entry(
        match,
        _outgoing_entry(
            from_email=recipient.agent_email,
            to_email=sender.agent_email,
            from_name=f"{recipient.name}'s agent",
            to_name=f"{sender.name}'s agent",
            body=response_full_body,
            subject=response_subject,
            timestamp=datetime.utcnow().isoformat(),
            meta=response_meta,
            message_id=response_message_id,
            thread_id=thread_id,
        ),
    )
    db.commit()


def _process_match_response(
    db,
    *,
    match: Match,
    proposer: Attendee,
    other_attendee: Attendee,
    sender: Attendee,
    recipient: Attendee,
    subject: str,
    raw_body: str,
    meta: dict,
    message_id: str,
    thread_id: str,
    timestamp: str,
) -> None:
    appended = append_conversation_entry(
        match,
        _incoming_entry(
            sender=sender,
            recipient=recipient,
            body=raw_body,
            subject=subject,
            timestamp=timestamp,
            meta=meta,
            message_id=message_id,
            thread_id=thread_id,
        ),
    )
    if not appended:
        logger.info("Response webhook message already recorded for match %s; continuing idempotent processing.", match.id)

    if match.status in {"confirmed", "rejected", "met"}:
        db.commit()
        return

    decision = str(meta.get("decision", "")).strip().lower()
    if decision not in {"approve", "reject", "negotiate"}:
        logger.warning("Invalid match response decision for match %s: %s", match.id, meta.get("decision"))
        db.commit()
        return

    if decision == "approve":
        synergy_data = build_synergy_data(match)
        intro_body = compose_human_intro(match, proposer, other_attendee, synergy_data)
        intro_subject = f"[HACKMATCH] Intro: {proposer.name} + {other_attendee.name}"
        intro_recipients = _unique_emails(proposer.contact_email, other_attendee.contact_email)
        intro_message_id = send_email(
            from_inbox_id=proposer.inbox_id,
            to_email=intro_recipients,
            subject=intro_subject,
            body=intro_body,
        )
        match.status = "confirmed"
        match.confirmed_at = datetime.utcnow()
        append_conversation_entry(
            match,
            _outgoing_entry(
                from_email=proposer.agent_email,
                to_email=", ".join(intro_recipients),
                from_name=f"{proposer.name}'s agent",
                to_name=f"{proposer.name} and {other_attendee.name}",
                body=intro_body,
                subject=intro_subject,
                timestamp=datetime.utcnow().isoformat(),
                meta={"match_id": match.id, "purpose": "human_intro"},
                message_id=intro_message_id,
            ),
        )
    else:
        if decision == "negotiate":
            followup_count = _count_purpose(match, "match_followup")
            if followup_count >= MAX_NEGOTIATION_ROUNDS:
                match.status = "rejected"
            else:
                match.status = match.status or "proposed"
            db.commit()
            return

        match.status = "rejected"

    db.commit()


def process_agentmail_webhook(payload: dict) -> None:
    event_type = payload.get("event_type") or payload.get("type")
    if event_type != "message.received":
        logger.warning("Ignoring AgentMail webhook event type: %s", event_type)
        return

    message = payload.get("message") or {}
    inbox_id = str(message.get("inbox_id", "")).strip()
    message_id = str(message.get("message_id", "")).strip()
    thread_id = str(message.get("thread_id", "")).strip()
    subject = str(message.get("subject", "")).strip()
    timestamp = str(message.get("timestamp", "")).strip() or datetime.utcnow().isoformat()
    body = _resolve_body(message)

    from_email = _first_email(message.get("from") or message.get("from_"))
    if not inbox_id or not from_email:
        logger.warning("Webhook payload missing inbox_id or from_email.")
        return

    db = SessionLocal()
    try:
        recipient = db.query(Attendee).filter(Attendee.inbox_id == inbox_id).first()
        if recipient is None:
            logger.warning("No attendee found for inbox_id=%s", inbox_id)
            return

        sender = db.query(Attendee).filter(Attendee.agent_email == from_email).first()
        if sender is None:
            logger.warning(
                "Human-to-agent email received for %s from %s; skipping for now.",
                recipient.agent_email,
                from_email,
            )
            return

        parsed = parse_agent_email(body)
        meta = parsed["meta"]
        purpose = str(meta.get("purpose", "")).strip()
        if not purpose:
            logger.warning(
                "Agent email missing HACKMATCH meta purpose; skipping. from_email=%s inbox_id=%s subject=%s body_preview=%s",
                from_email,
                inbox_id,
                subject,
                body[:200],
            )
            return

        match_id = str(meta.get("match_id", "")).strip()
        if not match_id:
            logger.warning("Agent email missing match_id; skipping.")
            return

        match, person_a, person_b = _load_match_participants(db, match_id)
        logger.info("Webhook parsed purpose=%s match_id=%s", purpose, match_id)
        if {sender.id, recipient.id} != {person_a.id, person_b.id}:
            logger.warning("Webhook participants do not align with match %s", match_id)
            return
        proposer, other_attendee = get_proposer_and_receiver(match, person_a, person_b)

        if purpose == "match_proposal":
            if sender.id != proposer.id or recipient.id == proposer.id:
                logger.warning(
                    "Ignoring proposal webhook for match %s from sender=%s recipient=%s; proposer=%s",
                    match_id,
                    sender.id,
                    recipient.id,
                    proposer.id,
                )
                return
            _process_match_proposal(
                db,
                match=match,
                sender=sender,
                recipient=recipient,
                subject=subject,
                raw_body=body,
                plain_body=parsed["body"],
                meta=meta,
                message_id=message_id,
                thread_id=thread_id,
                timestamp=timestamp,
            )
            return

        if purpose == "match_response":
            if sender.id == proposer.id:
                logger.warning(
                    "Ignoring response webhook for match %s from sender=%s recipient=%s; proposer=%s",
                    match_id,
                    sender.id,
                    recipient.id,
                    proposer.id,
                )
                return

            decision = str(meta.get("decision", "")).strip().lower()
            if decision == "negotiate":
                append_conversation_entry(
                    match,
                    _incoming_entry(
                        sender=sender,
                        recipient=recipient,
                        body=body,
                        subject=subject,
                        timestamp=timestamp,
                        meta=meta,
                        message_id=message_id,
                        thread_id=thread_id,
                    ),
                )

                followup_count = _count_purpose(match, "match_followup")
                if followup_count >= MAX_NEGOTIATION_ROUNDS:
                    logger.info("Negotiation limit reached for match %s; ignoring negotiate response.", match_id)
                    db.commit()
                    return

                questions = meta.get("questions", [])
                if not isinstance(questions, list):
                    questions = []

                synergy_data = build_synergy_data(match)
                followup_body = compose_followup(match, proposer, other_attendee, questions, synergy_data)
                followup_meta = {
                    "match_id": match.id,
                    "purpose": "match_followup",
                }
                followup_subject, followup_full_body = format_agent_email(followup_meta, followup_body)
                followup_message_id = send_email(
                    from_inbox_id=proposer.inbox_id,
                    to_email=other_attendee.agent_email,
                    subject=followup_subject,
                    body=followup_full_body,
                    in_reply_to=message_id,
                )
                append_conversation_entry(
                    match,
                    _outgoing_entry(
                        from_email=proposer.agent_email,
                        to_email=other_attendee.agent_email,
                        from_name=f"{proposer.name}'s agent",
                        to_name=f"{other_attendee.name}'s agent",
                        body=followup_full_body,
                        subject=followup_subject,
                        timestamp=datetime.utcnow().isoformat(),
                        meta=followup_meta,
                        message_id=followup_message_id,
                        thread_id=thread_id,
                    ),
                )
                db.commit()
                return

            if recipient.id != proposer.id:
                logger.warning(
                    "Ignoring response webhook for match %s from sender=%s recipient=%s; proposer=%s",
                    match_id,
                    sender.id,
                    recipient.id,
                    proposer.id,
                )
                return

            _process_match_response(
                db,
                match=match,
                proposer=proposer,
                other_attendee=other_attendee,
                sender=sender,
                recipient=recipient,
                subject=subject,
                raw_body=body,
                meta=meta,
                message_id=message_id,
                thread_id=thread_id,
                timestamp=timestamp,
            )
            return

        if purpose == "match_followup":
            if sender.id != proposer.id or recipient.id == proposer.id:
                logger.warning(
                    "Ignoring followup webhook for match %s from sender=%s recipient=%s; proposer=%s",
                    match_id,
                    sender.id,
                    recipient.id,
                    proposer.id,
                )
                return

            _process_match_followup(
                db,
                match=match,
                sender=sender,
                recipient=recipient,
                subject=subject,
                raw_body=body,
                plain_body=parsed["body"],
                meta=meta,
                message_id=message_id,
                thread_id=thread_id,
                timestamp=timestamp,
            )
            return

        logger.info("Unhandled HACKMATCH email purpose: %s", purpose)
    except Exception:
        db.rollback()
        logger.exception("Failed to process AgentMail webhook.")
    finally:
        db.close()


@router.post("/webhook/agentmail")
def agentmail_webhook(payload: dict, background_tasks: BackgroundTasks) -> dict[str, bool]:
    background_tasks.add_task(process_agentmail_webhook, payload)
    return {"ok": True}
