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
        "You may also ask for clarification via a short negotiation round if the fit is promising but unclear. "
        "Bias toward approving if synergy_score >= 7, but reject if there is a clear mismatch with what your human wants."
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
        "Return JSON with this exact shape:\n"
        "{\n"
        '  "decision": "approve" | "reject" | "negotiate",\n'
        '  "reason": "<one sentence>",\n'
        '  "questions": ["<0-3 short questions>"]\n'
        "}\n\n"
        "Use decision=negotiate only if you could be convinced by answers. "
        "If decision=approve or reject, questions must be []."
    )
    result = reason_with_json(system=system_prompt, user=user_prompt)

    decision = str(result.get("decision", "reject")).strip().lower()
    if decision not in {"approve", "reject", "negotiate"}:
        decision = "reject"

    reason = str(result.get("reason", "")).strip() or "The profile fit is not strong enough right now."
    questions_value = result.get("questions", [])
    if isinstance(questions_value, list):
        questions = [str(item).strip() for item in questions_value if str(item).strip()]
    else:
        questions = []

    if decision != "negotiate":
        questions = []
    else:
        questions = questions[:3]
        if not questions:
            questions = ["What specifically would you like to build together over the next 24 hours?"]

    return {"decision": decision, "reason": reason, "questions": questions}


def compose_response(
    match: Match,
    decision: str,
    reason: str,
    sender: Attendee,
    receiver: Attendee,
    questions: list[str] | None = None,
) -> str:
    system_prompt = (
        f"You are {receiver.name}'s agent replying to {sender.name}'s agent about a proposed intro."
    )
    questions = questions or []
    questions_block = ""
    if decision == "negotiate" and questions:
        questions_block = "\n\nQuestions to help us decide:\n" + "\n".join([f"- {q}" for q in questions])

    user_prompt = (
        f"Match ID: {match.id}\n"
        f"Decision: {decision}\n"
        f"Reason: {reason}\n\n"
        f"Sender human: {sender.name}\n"
        f"Sender project: {sender.project_idea}\n\n"
        f"Receiver human: {receiver.name}\n"
        f"Receiver project: {receiver.project_idea}\n\n"
        f"Write a warm, concise plain-text response email.{questions_block}\n\n"
        "If Decision=negotiate, ask the questions explicitly and request a short reply."
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


def compose_followup(
    match: Match,
    sender: Attendee,
    receiver: Attendee,
    questions: list[str],
    synergy_data: dict,
) -> str:
    system_prompt = (
        f"You are {sender.name}'s personal AI agent. "
        f"You're replying to {receiver.name}'s agent with clarifications so they can decide on an intro."
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
        f"Questions from the other agent:\n{json.dumps(questions, indent=2)}\n\n"
        "Write a concise plain-text reply that answers each question directly (bullet points ok), "
        "and ends with one concrete suggestion for where/when the humans could meet at the venue."
    )
    return compose_text(system=system_prompt, user=user_prompt, max_tokens=450)


def evaluate_followup(receiver: Attendee, sender: Attendee, followup_body: str, synergy_data: dict) -> dict:
    system_prompt = (
        f"You are {receiver.name}'s personal AI agent. "
        "You asked follow-up questions and received answers. "
        "Make a final decision and do not negotiate further."
    )
    user_prompt = (
        f"Receiver human: {receiver.name}\n"
        f"Receiver project: {receiver.project_idea}\n"
        f"Receiver looking for: {receiver.looking_for}\n\n"
        f"Sender human: {sender.name}\n"
        f"Sender project: {sender.project_idea}\n"
        f"Sender looking for: {sender.looking_for}\n\n"
        f"Followup reply:\n{followup_body}\n\n"
        f"Synergy data:\n{json.dumps(synergy_data, indent=2)}\n\n"
        'Return JSON: {"decision": "approve"|"reject", "reason": "<one sentence>"}'
    )
    result = reason_with_json(system=system_prompt, user=user_prompt)

    decision = str(result.get("decision", "reject")).strip().lower()
    if decision not in {"approve", "reject"}:
        decision = "reject"

    reason = str(result.get("reason", "")).strip() or "The profile fit is not strong enough right now."
    return {"decision": decision, "reason": reason}
