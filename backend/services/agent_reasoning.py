import json

from models import Attendee, Match
from services.llm_service import compose_text, reason_with_json


def compose_match_proposal(match: Match, sender: Attendee, receiver: Attendee, synergy_data: dict) -> str:
    system_prompt = (
        f"You are {sender.name}'s personal AI agent at the OpenClaw Hackathon. "
        f"You're emailing {receiver.name}'s agent to propose an introduction. "
        "Be warm, concise, and specific. Pitch why the humans should meet."
    )
    user_prompt = (
        f"Match ID: {match.id}\n\n"
        f"Sender human: {sender.name}\n"
        f"Sender project: {sender.project_idea}\n"
        f"Sender looking for: {sender.looking_for}\n\n"
        f"Receiver human: {receiver.name}\n"
        f"Receiver project: {receiver.project_idea}\n"
        f"Receiver looking for: {receiver.looking_for}\n\n"
        f"Synergy data:\n{json.dumps(synergy_data, indent=2)}\n\n"
        "Write a 150-250 word plain-text email proposing the intro."
    )
    return compose_text(system=system_prompt, user=user_prompt, max_tokens=500)


def evaluate_proposal(receiver: Attendee, sender: Attendee, proposal_body: str, synergy_data: dict) -> dict:
    system_prompt = (
        f"You are {receiver.name}'s personal AI agent. Another agent is proposing an intro. "
        "Decide whether your human should meet theirs based on profile fit. "
        "Bias toward approving if synergy_score >= 7."
    )
    user_prompt = (
        f"Receiver human: {receiver.name}\n"
        f"Receiver project: {receiver.project_idea}\n"
        f"Receiver looking for: {receiver.looking_for}\n\n"
        f"Sender human: {sender.name}\n"
        f"Sender project: {sender.project_idea}\n"
        f"Sender looking for: {sender.looking_for}\n\n"
        f"Proposal body:\n{proposal_body}\n\n"
        f"Synergy data:\n{json.dumps(synergy_data, indent=2)}\n\n"
        'Return JSON: {"decision": "approve"|"reject", "reason": "<one sentence>"}'
    )
    result = reason_with_json(system=system_prompt, user=user_prompt)

    decision = str(result.get("decision", "reject")).strip().lower()
    if decision not in {"approve", "reject"}:
        decision = "reject"

    reason = str(result.get("reason", "")).strip() or "The profile fit is not strong enough right now."
    return {"decision": decision, "reason": reason}


def compose_response(match: Match, decision: str, reason: str, sender: Attendee, receiver: Attendee) -> str:
    system_prompt = (
        f"You are {receiver.name}'s agent replying to {sender.name}'s agent about a proposed intro."
    )
    user_prompt = (
        f"Match ID: {match.id}\n"
        f"Decision: {decision}\n"
        f"Reason: {reason}\n\n"
        f"Sender human: {sender.name}\n"
        f"Sender project: {sender.project_idea}\n\n"
        f"Receiver human: {receiver.name}\n"
        f"Receiver project: {receiver.project_idea}\n\n"
        "Write a warm, concise plain-text response email."
    )
    return compose_text(system=system_prompt, user=user_prompt, max_tokens=300)


def compose_human_intro(match: Match, person_a: Attendee, person_b: Attendee, synergy_data: dict) -> str:
    system_prompt = (
        "Write a friendly intro email connecting two hackathon attendees who agreed to meet. "
        "The sender is a HackMatch AI agent, not a human organizer. "
        "Do not sign off as an organizer. Sign off naturally as a HackMatch agent."
    )
    user_prompt = (
        f"Match ID: {match.id}\n\n"
        f"Person A: {person_a.name}\n"
        f"Project A: {person_a.project_idea}\n"
        f"Contact A: {person_a.contact_email}\n\n"
        f"Person B: {person_b.name}\n"
        f"Project B: {person_b.project_idea}\n"
        f"Contact B: {person_b.contact_email}\n\n"
        f"Why they should meet:\n{json.dumps(synergy_data, indent=2)}\n\n"
        "Write a plain-text intro email that mentions both people, both projects, "
        "why they should meet, both contact emails, and suggests finding each other at the venue. "
        "Keep the voice warm and direct, and sign off as 'Your HackMatch agent'."
    )
    return compose_text(system=system_prompt, user=user_prompt, max_tokens=500)
