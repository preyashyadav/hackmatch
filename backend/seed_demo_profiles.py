import asyncio
import json
import logging
import re
from urllib.parse import urljoin

import config
from db import SessionLocal
from models import Attendee
from services.agentmail_service import create_inbox, ensure_webhook_registration
from services.embeddings import embed
from services.nia_service import index_text


logger = logging.getLogger(__name__)


DEMO_PROFILES = [
    {
        "name": "Preyash Yadav",
        "contact_email": "preyash.me@gmail.com",
        "project_idea": (
            "An AI operations platform that helps teams build, deploy, and monitor autonomous agents "
            "with strong backend infrastructure, full-stack workflows, and model evaluation loops."
        ),
        "looking_for": (
            "Backend engineers, full-stack engineers, and AI/ML engineers building agent systems."
        ),
        "is_persona": False,
    },
    {
        "name": "Daniel Boudagian",
        "contact_email": "djboudagian@gmail.com",
        "project_idea": (
            "A frontend analytics workspace for operations teams that turns messy business data into "
            "clean dashboards, reports, and workflow decisions."
        ),
        "looking_for": "Frontend engineers, data analysts, and product-minded people who love dashboards.",
        "is_persona": False,
    },
    {
        "name": "Marcus Reed",
        "contact_email": "marcus.reed@hackmatch.local",
        "project_idea": (
            "A backend orchestration service for multi-agent workflows with retries, queues, "
            "rollback trails, and audit logs."
        ),
        "looking_for": "Backend engineers, distributed systems builders, and infra people.",
        "is_persona": True,
    },
    {
        "name": "Zoe Park",
        "contact_email": "zoe.park@hackmatch.local",
        "project_idea": (
            "A design-to-code agent that turns Figma flows into React screens and ships UI "
            "experiments for product teams."
        ),
        "looking_for": "Frontend engineers, design engineers, and product designers.",
        "is_persona": True,
    },
    {
        "name": "Nisha Rao",
        "contact_email": "nisha.rao@hackmatch.local",
        "project_idea": (
            "An LLM evaluation platform that scores agent responses, detects regressions, "
            "and suggests prompt fixes before deployment."
        ),
        "looking_for": "AI/ML engineers, eval researchers, and backend infra folks.",
        "is_persona": True,
    },
    {
        "name": "Imani Cole",
        "contact_email": "imani.cole@hackmatch.local",
        "project_idea": (
            "A customer support copilot that fine-tunes routing models and summarizes ticket "
            "sentiment across email, chat, and voice."
        ),
        "looking_for": "ML engineers, NLP researchers, and support ops builders.",
        "is_persona": True,
    },
    {
        "name": "Rafael Torres",
        "contact_email": "rafael.torres@hackmatch.local",
        "project_idea": (
            "A real-time voice agent platform for sales teams with latency monitoring, "
            "call coaching, and CRM follow-up automation."
        ),
        "looking_for": "Backend engineers, speech ML engineers, and frontend builders for agent UX.",
        "is_persona": True,
    },
    {
        "name": "Mei Tan",
        "contact_email": "mei.tan@hackmatch.local",
        "project_idea": (
            "A computer vision quality-control agent for warehouse lines that spots defects "
            "and triggers follow-up actions for operators."
        ),
        "looking_for": "ML engineers, computer vision researchers, and backend engineers.",
        "is_persona": True,
    },
]


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "demo"


def _profile_text(profile: dict) -> str:
    return f"{profile['project_idea']} {profile['looking_for']}"


def _profile_summary(profile: dict) -> str:
    return (
        f"{profile['name']} is building: {profile['project_idea']}. "
        f"Looking for: {profile['looking_for']}."
    )


async def _sync_nia_source(attendee: Attendee, profile: dict) -> None:
    try:
        attendee.nia_source_id = await index_text(_profile_summary(profile), name=f"attendee_{attendee.id}")
    except Exception:
        logger.exception("Failed to index attendee %s in Nia.", attendee.id)


def _ensure_webhook(inbox_id: str) -> None:
    if not config.WEBHOOK_BASE_URL:
        return

    webhook_url = urljoin(config.WEBHOOK_BASE_URL.rstrip("/") + "/", "webhook/agentmail")
    ensure_webhook_registration(inbox_id, webhook_url)


async def main() -> None:
    session = SessionLocal()
    try:
        for index, profile in enumerate(DEMO_PROFILES, start=1):
            attendees = (
                session.query(Attendee)
                .filter(Attendee.contact_email == profile["contact_email"])
                .order_by(Attendee.created_at.asc())
                .all()
            )

            attendee = attendees[0] if attendees else None
            duplicate_attendees = attendees[1:] if len(attendees) > 1 else []
            for duplicate in duplicate_attendees:
                session.delete(duplicate)
            if duplicate_attendees:
                session.commit()
                print(
                    f"[{index}/{len(DEMO_PROFILES)}] Removed {len(duplicate_attendees)} duplicate row(s) for "
                    f"{profile['contact_email']}"
                )

            if attendee is None:
                inbox = create_inbox(_slugify(profile["name"]))
                _ensure_webhook(inbox["inbox_id"])

                attendee = Attendee(
                    name=profile["name"],
                    contact_email=profile["contact_email"],
                    agent_email=inbox["agent_email"],
                    inbox_id=inbox["inbox_id"],
                    project_idea=profile["project_idea"],
                    looking_for=profile["looking_for"],
                    embedding=json.dumps(embed(_profile_text(profile))),
                    is_persona=bool(profile["is_persona"]),
                )
                session.add(attendee)
                session.flush()
                await _sync_nia_source(attendee, profile)
                session.commit()
                session.refresh(attendee)
                print(
                    f"[{index}/{len(DEMO_PROFILES)}] Created {attendee.name} "
                    f"({attendee.contact_email}) -> {attendee.agent_email}"
                )
                continue

            attendee.name = profile["name"]
            attendee.project_idea = profile["project_idea"]
            attendee.looking_for = profile["looking_for"]
            attendee.embedding = json.dumps(embed(_profile_text(profile)))
            attendee.is_persona = bool(profile["is_persona"])
            _ensure_webhook(attendee.inbox_id)
            await _sync_nia_source(attendee, profile)
            session.add(attendee)
            session.commit()
            print(
                f"[{index}/{len(DEMO_PROFILES)}] Updated {attendee.name} "
                f"({attendee.contact_email}) -> {attendee.agent_email}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
