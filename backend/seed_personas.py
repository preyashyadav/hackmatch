import asyncio
import re

import httpx

import config
from db import SessionLocal
from models import Attendee


PERSONAS = [
    {
        "name": "Maya Chen",
        "project_idea": "An agent runtime that deploys customer support inbox agents with approval checkpoints and real email actions.",
        "looking_for": "Infra engineers, prompt engineers, and founders building agent operations products.",
    },
    {
        "name": "Arjun Patel",
        "project_idea": "Email-native procurement agents that negotiate software renewals and collect quotes from vendors automatically.",
        "looking_for": "B2B SaaS operators, GTM engineers, and people who know procurement workflows.",
    },
    {
        "name": "Sofia Martinez",
        "project_idea": "A multi-agent quality system for hardware teams that reads test logs, files bugs, and coordinates reruns.",
        "looking_for": "Hardware builders, robotics engineers, and agent memory infrastructure people.",
    },
    {
        "name": "Jordan Kim",
        "project_idea": "An observability layer for autonomous agents that records decisions, tool calls, and rollback trails for audits.",
        "looking_for": "Agent platform teams, security folks, and people building evaluation tooling.",
    },
    {
        "name": "Elena Rossi",
        "project_idea": "Security guardrail agents that inspect outbound tool calls and redact risky actions before execution.",
        "looking_for": "Security engineers, LLM infra builders, and compliance-minded founders.",
    },
    {
        "name": "Noah Brooks",
        "project_idea": "An agent that handles cross-border contractor payouts, invoice follow-ups, and compliance reminders for startups.",
        "looking_for": "Payments APIs experts, fintech designers, and SMB finance operators.",
    },
    {
        "name": "Priya Shah",
        "project_idea": "A chargeback defense copilot that drafts evidence packets and chases merchants for missing documentation.",
        "looking_for": "Fintech backend engineers, risk teams, and anyone who has worked on card disputes.",
    },
    {
        "name": "Omar Hassan",
        "project_idea": "An invoice factoring assistant for small suppliers that analyzes receivables and proactively negotiates advance offers.",
        "looking_for": "Lenders, underwriters, and engineers with cash flow or B2B finance experience.",
    },
    {
        "name": "Lila Nguyen",
        "project_idea": "A conversational budgeting agent that can email banks, monitor recurring spend, and renegotiate subscriptions.",
        "looking_for": "Consumer fintech builders, data scientists, and growth-minded product people.",
    },
    {
        "name": "Aisha Rahman",
        "project_idea": "A clinical trial matching agent that screens patient notes, emails study coordinators, and manages follow-up logistics.",
        "looking_for": "Healthcare AI researchers, compliance experts, and medical workflow builders.",
    },
    {
        "name": "Ben Carter",
        "project_idea": "A prior authorization drafting assistant that gathers insurer requirements and prepares submission packets for clinics.",
        "looking_for": "Healthtech founders, EHR integrators, and anyone who knows payer workflows.",
    },
    {
        "name": "Chloe Park",
        "project_idea": "A home-health triage agent that routes patient updates, escalates urgent changes, and coordinates caregiver check-ins.",
        "looking_for": "Care delivery operators, HIPAA-aware engineers, and voice or messaging specialists.",
    },
    {
        "name": "Ethan Wu",
        "project_idea": "A flaky test triage agent that reads CI failures, opens concise bug reports, and suggests likely root causes.",
        "looking_for": "Dev tools hackers, compiler people, and engineering productivity teams.",
    },
    {
        "name": "Grace Lin",
        "project_idea": "A docs-to-code migration agent that reads legacy runbooks and turns them into checked-in automation scripts.",
        "looking_for": "Platform engineers, technical writers, and internal tooling builders.",
    },
    {
        "name": "Marcus Bell",
        "project_idea": "An incident response agent that coordinates pager escalations, status updates, and postmortem evidence collection.",
        "looking_for": "SREs, observability builders, and security response engineers.",
    },
    {
        "name": "Tessa Moore",
        "project_idea": "A personal shopping agent for DTC brands that handles reorder reminders and concierge upsells over email and SMS.",
        "looking_for": "E-commerce operators, retention marketers, and conversational UX designers.",
    },
    {
        "name": "Diego Alvarez",
        "project_idea": "A travel rebooking concierge that watches flight disruptions and proactively secures better alternatives for travelers.",
        "looking_for": "Travel APIs experts, consumer product designers, and operations automators.",
    },
    {
        "name": "Nina Kapoor",
        "project_idea": "A creator merch agent that coordinates suppliers, answers fan questions, and automates limited-drop launches.",
        "looking_for": "Consumer app founders, supply chain hackers, and growth engineers.",
    },
    {
        "name": "Cole Mercer",
        "project_idea": "A ranch operations agent that ingests drone footage, flags cattle health issues, and coordinates field crew dispatch.",
        "looking_for": "Drone autonomy people, agtech founders, and computer vision engineers.",
    },
    {
        "name": "Imani Okafor",
        "project_idea": "A space operations assistant that helps satellite teams schedule tasks, detect conjunction risks, and coordinate responses.",
        "looking_for": "Aerospace software engineers, mapping people, and optimization experts.",
    },
]


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "persona"


async def main() -> None:
    base_url = config.BACKEND_BASE_URL.rstrip("/")
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        for index, persona in enumerate(PERSONAS, start=1):
            slug = _slugify(persona["name"])
            payload = {
                "name": persona["name"],
                "contact_email": f"{slug}@hackmatch.local",
                "project_idea": persona["project_idea"],
                "looking_for": persona["looking_for"],
            }

            print(f"[{index}/{len(PERSONAS)}] Signing up {persona['name']}...")
            response = await client.post("/signup", json=payload)
            response.raise_for_status()
            data = response.json()

            session = SessionLocal()
            try:
                attendee = session.query(Attendee).filter(Attendee.id == data["attendee_id"]).first()
                if attendee is None:
                    raise RuntimeError(f"Could not find attendee row for {persona['name']}.")
                attendee.is_persona = True
                session.commit()
            finally:
                session.close()

            print(
                f"[{index}/{len(PERSONAS)}] Created {persona['name']} "
                f"({data['attendee_id']}) -> {data['agent_email']}"
            )


if __name__ == "__main__":
    asyncio.run(main())
