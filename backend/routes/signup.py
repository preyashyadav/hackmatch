import json
import logging
import re
from urllib.parse import urljoin

import email_validator
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

import config
from db import get_db
from models import Attendee
from services.agentmail_service import create_inbox, ensure_webhook_registration, send_email
from services.embeddings import embed
from services.nia_service import index_text


logger = logging.getLogger(__name__)
router = APIRouter()

if "local" in email_validator.SPECIAL_USE_DOMAIN_NAMES:
    email_validator.SPECIAL_USE_DOMAIN_NAMES.remove("local")


class SignupRequest(BaseModel):
    name: str
    contact_email: EmailStr
    project_idea: str
    looking_for: str


class SignupResponse(BaseModel):
    attendee_id: str
    agent_email: str


def _username_hint(name: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]", "", name.lower())
    return (sanitized or "agent")[:12]


def _welcome_body(name: str, project_idea: str, looking_for: str) -> str:
    return (
        f"Hi {name},\n\n"
        "I'm your match-making agent. I've got your profile:\n"
        f"- Building: {project_idea}\n"
        f"- Looking for: {looking_for}\n\n"
        "I'll start scouting matches now and email you when I find good matches.\n\n"
        "You can email me anytime at this address to update your interests.\n\n"
        "— Your HackMatch agent"
    )


@router.post("/signup", response_model=SignupResponse)
async def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    try:
        inbox = create_inbox(_username_hint(payload.name))
    except httpx.HTTPError as exc:
        logger.exception("AgentMail inbox provisioning failed during signup.")
        raise HTTPException(
            status_code=502,
            detail="AgentMail inbox provisioning is temporarily unavailable. Please retry signup.",
        ) from exc

    profile_text = f"{payload.project_idea} {payload.looking_for}"
    profile_embedding = embed(profile_text)

    attendee = Attendee(
        name=payload.name,
        contact_email=str(payload.contact_email),
        agent_email=inbox["agent_email"],
        inbox_id=inbox["inbox_id"],
        project_idea=payload.project_idea,
        looking_for=payload.looking_for,
        embedding=json.dumps(profile_embedding),
        is_persona=False,
    )

    try:
        db.add(attendee)
        db.flush()

        if config.WEBHOOK_BASE_URL:
            webhook_url = urljoin(config.WEBHOOK_BASE_URL.rstrip("/") + "/", "webhook/agentmail")
            try:
                ensure_webhook_registration(inbox["inbox_id"], webhook_url)
            except Exception:
                logger.exception("Failed to register AgentMail webhook for attendee %s", attendee.id)
        else:
            logger.warning("WEBHOOK_BASE_URL is not configured; skipping webhook registration.")

        send_email(
            from_inbox_id=inbox["inbox_id"],
            to_email=str(payload.contact_email),
            subject="👋 I'm your HackMatch agent",
            body=_welcome_body(payload.name, payload.project_idea, payload.looking_for),
        )

        db.commit()
        db.refresh(attendee)
    except Exception:
        db.rollback()
        raise

    profile_summary = (
        f"{payload.name} is building: {payload.project_idea}. "
        f"Looking for: {payload.looking_for}."
    )
    try:
        attendee.nia_source_id = await index_text(profile_summary, name=f"attendee_{attendee.id}")
        db.add(attendee)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to index attendee %s in Nia.", attendee.id)

    return SignupResponse(attendee_id=attendee.id, agent_email=attendee.agent_email)
