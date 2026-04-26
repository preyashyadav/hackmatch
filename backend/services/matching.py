import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from models import Attendee, Match
from services.agent_reasoning import compose_match_proposal
from services.agentmail_service import send_email
from services.llm_service import reason_with_json
from services.nia_service import search as nia_search
from utils.email_format import format_agent_email


logger = logging.getLogger(__name__)
NIA_SOURCES_PATH = Path(__file__).resolve().parent.parent / ".nia_sources.json"

try:
    NIA_SOURCES = json.loads(NIA_SOURCES_PATH.read_text())
except Exception:
    NIA_SOURCES = {}


def _parse_embedding(attendee: Attendee) -> list[float]:
    return json.loads(attendee.embedding)


def _canonical_pair(a_id: str, b_id: str) -> tuple[str, str]:
    return tuple(sorted((a_id, b_id)))


def pair_key_for_ids(a_id: str, b_id: str) -> str:
    left_id, right_id = _canonical_pair(a_id, b_id)
    return f"{left_id}:{right_id}"


def _clamp_score(value: float) -> float:
    return max(0.0, min(10.0, float(value)))


def _normalize_overlap_reasons(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe_strings(values: list[str | None]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = str(value or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _format_nia_context(results: list[dict]) -> str:
    if not results:
        return ""

    lines = ["## Wider context (from indexed sources):"]
    for item in results:
        snippet = str(item.get("snippet", "")).strip()
        source = str(item.get("source", "")).strip()
        if not snippet:
            continue
        if source:
            lines.append(f"- {source}: {snippet}")
        else:
            lines.append(f"- {snippet}")

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _load_agent_conversation(match: Match) -> list[dict]:
    try:
        conversation = json.loads(match.agent_conversation or "[]")
    except json.JSONDecodeError:
        return []
    return conversation if isinstance(conversation, list) else []


def _save_agent_conversation(match: Match, conversation: list[dict]) -> None:
    match.agent_conversation = json.dumps(conversation)


def make_preview(text: str) -> str:
    return " ".join(text.split())[:100]


def build_synergy_data(match: Match) -> dict:
    return {
        "overlap_reasons": json.loads(match.overlap_reasons or "[]"),
        "potential_collaboration": match.potential_collaboration,
        "relevant_external_context": match.relevant_external_context,
        "synergy_score": match.synergy_score,
        "theme_alignment_a": match.theme_alignment_a_score,
        "theme_alignment_b": match.theme_alignment_b_score,
    }


def append_conversation_entry(match: Match, entry: dict) -> bool:
    conversation = _load_agent_conversation(match)
    message_id = entry.get("message_id")
    if message_id and any(item.get("message_id") == message_id for item in conversation):
        return False

    conversation.append(entry)
    _save_agent_conversation(match, conversation)
    return True


def _load_match_with_attendees(match_id: str, db_session) -> tuple[Match, Attendee, Attendee]:
    match = db_session.query(Match).filter(Match.id == match_id).first()
    if match is None:
        raise ValueError("Match not found")

    attendee_a = db_session.query(Attendee).filter(Attendee.id == match.attendee_a_id).first()
    attendee_b = db_session.query(Attendee).filter(Attendee.id == match.attendee_b_id).first()
    if attendee_a is None or attendee_b is None:
        raise ValueError("Match attendees not found")

    return match, attendee_a, attendee_b


def get_proposer_and_receiver(match: Match, attendee_a: Attendee, attendee_b: Attendee) -> tuple[Attendee, Attendee]:
    if match.proposer_attendee_id == attendee_b.id:
        return attendee_b, attendee_a
    if match.proposer_attendee_id not in {attendee_a.id, attendee_b.id}:
        logger.warning(
            "Match %s has invalid proposer_attendee_id=%s; defaulting to attendee_a_id=%s",
            match.id,
            match.proposer_attendee_id,
            attendee_a.id,
        )
    return attendee_a, attendee_b


def cosine_similarity(a: list[float], b: list[float]) -> float:
    vector_a = np.array(a, dtype=float)
    vector_b = np.array(b, dtype=float)

    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return float(np.dot(vector_a, vector_b) / (norm_a * norm_b))


def find_candidates(attendee: Attendee, all_attendees: list[Attendee], top_k: int = 5) -> list[tuple[Attendee, float]]:
    attendee_embedding = _parse_embedding(attendee)
    scored_candidates: list[tuple[Attendee, float]] = []

    for candidate in all_attendees:
        if candidate.id == attendee.id:
            continue
        similarity = cosine_similarity(attendee_embedding, _parse_embedding(candidate))
        scored_candidates.append((candidate, similarity))

    scored_candidates.sort(key=lambda item: item[1], reverse=True)
    return scored_candidates[:top_k]


async def score_synergy(a: Attendee, b: Attendee, nia_source_ids: list[str] | None = None) -> dict:
    source_ids = _dedupe_strings(
        [
            a.nia_source_id,
            b.nia_source_id,
            *(nia_source_ids or []),
            NIA_SOURCES.get("event_doc"),
            NIA_SOURCES.get("yc_w26"),
            NIA_SOURCES.get("agentmail_docs"),
            NIA_SOURCES.get("nia_docs"),
        ]
    )

    wider_context = ""
    if source_ids:
        results = await nia_search(
            query=(
                f"How do '{a.project_idea}' and '{b.project_idea}' relate to the OpenClaw theme "
                "'agents that act in the world'? Consider technical overlap, fit with the "
                "AgentMail or Nia build patterns, and only secondarily any relevant YC W26 companies."
            ),
            source_ids=source_ids,
            limit=5,
        )
        wider_context = _format_nia_context(results)

    system_prompt = (
        "You are evaluating networking matches for the OpenClaw Hackathon. "
        'The theme is "agents that act in the world." '
        "Score how strong this pairing is for collaboration, with extra weight on "
        "real-world actionability, complementary skills, and whether both projects fit the theme. "
        "Prioritize the OpenClaw theme and event framing over generic startup similarity. "
        "If wider context is provided, use it to enrich relevant_external_context with concise references "
        "to OpenClaw, AgentMail or Nia build patterns, and only then YC W26 companies or related work."
    )
    user_prompt = (
        "Evaluate this pair and return the required JSON.\n\n"
        f"Attendee A\nName: {a.name}\nProject idea: {a.project_idea}\nLooking for: {a.looking_for}\n\n"
        f"Attendee B\nName: {b.name}\nProject idea: {b.project_idea}\nLooking for: {b.looking_for}\n\n"
        f"{wider_context}\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "synergy_score": <0-10>,\n'
        '  "theme_alignment_a": <0-10>,\n'
        '  "theme_alignment_b": <0-10>,\n'
        '  "overlap_reasons": [<2-4 short strings>],\n'
        '  "potential_collaboration": <one-paragraph string>,\n'
        '  "relevant_external_context": <string, can be empty>\n'
        "}\n\n"
        "If no useful wider context exists, relevant_external_context may be empty."
    )

    result = reason_with_json(system=system_prompt, user=user_prompt)

    return {
        "synergy_score": _clamp_score(result.get("synergy_score", 0.0)),
        "theme_alignment_a": _clamp_score(result.get("theme_alignment_a", 0.0)),
        "theme_alignment_b": _clamp_score(result.get("theme_alignment_b", 0.0)),
        "overlap_reasons": _normalize_overlap_reasons(result.get("overlap_reasons", [])),
        "potential_collaboration": str(result.get("potential_collaboration", "")).strip(),
        "relevant_external_context": str(result.get("relevant_external_context", "")).strip(),
    }


def propose_match(match_id: str, db_session) -> None:
    match, attendee_a, attendee_b = _load_match_with_attendees(match_id, db_session)
    if match.status != "proposed":
        return

    proposer, receiver = get_proposer_and_receiver(match, attendee_a, attendee_b)
    synergy_data = build_synergy_data(match)
    proposal_body = compose_match_proposal(match, proposer, receiver, synergy_data)
    meta = {
        "match_id": match.id,
        "purpose": "match_proposal",
        "synergy_score": match.synergy_score,
    }
    subject, full_body = format_agent_email(meta, proposal_body)
    message_id = send_email(
        from_inbox_id=proposer.inbox_id,
        to_email=receiver.agent_email,
        subject=subject,
        body=full_body,
    )

    append_conversation_entry(
        match,
        {
            "from_email": proposer.agent_email,
            "to_email": receiver.agent_email,
            "from_name": f"{proposer.name}'s agent",
            "to_name": f"{receiver.name}'s agent",
            "direction": "outgoing",
            "preview": make_preview(full_body),
            "full_body": full_body,
            "subject": subject,
            "timestamp": datetime.utcnow().isoformat(),
            "meta": meta,
            "message_id": message_id,
        },
    )
    db_session.commit()


async def run_matching_for(attendee_id: str, db_session) -> int:
    attendee = db_session.query(Attendee).filter(Attendee.id == attendee_id).first()
    if attendee is None:
        raise ValueError("Attendee not found")

    other_attendees = db_session.query(Attendee).filter(Attendee.id != attendee_id).all()
    existing_matches = (
        db_session.query(Match)
        .filter(or_(Match.attendee_a_id == attendee_id, Match.attendee_b_id == attendee_id))
        .all()
    )
    existing_pair_keys = {
        match.pair_key or pair_key_for_ids(match.attendee_a_id, match.attendee_b_id)
        for match in existing_matches
    }

    candidates = find_candidates(attendee, other_attendees, top_k=5)
    created_count = 0
    new_match_ids: list[str] = []
    theme_scores: list[float] = []

    for candidate, _ in candidates:
        pair = _canonical_pair(attendee.id, candidate.id)
        pair_key = pair_key_for_ids(attendee.id, candidate.id)
        if pair_key in existing_pair_keys:
            continue

        result = await score_synergy(attendee, candidate)
        theme_scores.append(result["theme_alignment_a"])

        if result["synergy_score"] < 6.0:
            continue

        if attendee.id == pair[0]:
            theme_alignment_a_score = result["theme_alignment_a"]
            theme_alignment_b_score = result["theme_alignment_b"]
        else:
            theme_alignment_a_score = result["theme_alignment_b"]
            theme_alignment_b_score = result["theme_alignment_a"]

        match = Match(
            attendee_a_id=pair[0],
            attendee_b_id=pair[1],
            proposer_attendee_id=attendee.id,
            pair_key=pair_key,
            status="proposed",
            synergy_score=result["synergy_score"],
            theme_alignment_score=(theme_alignment_a_score + theme_alignment_b_score) / 2.0,
            theme_alignment_a_score=theme_alignment_a_score,
            theme_alignment_b_score=theme_alignment_b_score,
            overlap_reasons=json.dumps(result["overlap_reasons"]),
            potential_collaboration=result["potential_collaboration"],
            relevant_external_context=result["relevant_external_context"],
            agent_conversation="[]",
        )
        try:
            with db_session.begin_nested():
                db_session.add(match)
                db_session.flush()
        except IntegrityError:
            logger.warning("Skipped duplicate match for pair %s", pair_key)
            continue

        existing_pair_keys.add(pair_key)
        created_count += 1
        new_match_ids.append(match.id)

    if theme_scores:
        attendee.theme_alignment_score = float(np.mean(theme_scores))

    db_session.commit()

    for match_id in new_match_ids:
        try:
            propose_match(match_id, db_session)
        except Exception:
            db_session.rollback()
            logger.exception("Failed to send proposal email for match %s", match_id)

    return created_count
