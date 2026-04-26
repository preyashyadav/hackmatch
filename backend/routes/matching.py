import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from db import get_db
from models import Attendee, Match
from services.matching import run_matching_for


router = APIRouter()


class RefreshResponse(BaseModel):
    ok: bool
    matches_found: int


class OtherAttendeeResponse(BaseModel):
    id: str
    name: str
    contact_email: str
    project_idea: str
    looking_for: str


class MatchResponse(BaseModel):
    match_id: str
    status: str
    other_attendee: OtherAttendeeResponse
    synergy_score: float
    theme_alignment_score: float
    overlap_reasons: list[str]
    potential_collaboration: str
    relevant_external_context: str
    created_at: datetime
    confirmed_at: datetime | None


@router.post("/attendees/{attendee_id}/refresh", response_model=RefreshResponse)
async def refresh_matches(attendee_id: str, db: Session = Depends(get_db)) -> RefreshResponse:
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")

    matches_found = await run_matching_for(attendee_id, db)
    return RefreshResponse(ok=True, matches_found=matches_found)


@router.get("/attendees/{attendee_id}/matches", response_model=list[MatchResponse])
def list_matches(attendee_id: str, db: Session = Depends(get_db)) -> list[MatchResponse]:
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")

    matches = (
        db.query(Match)
        .filter(or_(Match.attendee_a_id == attendee_id, Match.attendee_b_id == attendee_id))
        .all()
    )

    response: list[MatchResponse] = []
    for match in matches:
        other_attendee_id = match.attendee_b_id if match.attendee_a_id == attendee_id else match.attendee_a_id
        other_attendee = db.query(Attendee).filter(Attendee.id == other_attendee_id).first()
        if other_attendee is None:
            continue

        response.append(
            MatchResponse(
                match_id=match.id,
                status=match.status,
                other_attendee=OtherAttendeeResponse(
                    id=other_attendee.id,
                    name=other_attendee.name,
                    contact_email=other_attendee.contact_email,
                    project_idea=other_attendee.project_idea,
                    looking_for=other_attendee.looking_for,
                ),
                synergy_score=match.synergy_score,
                theme_alignment_score=match.theme_alignment_score,
                overlap_reasons=json.loads(match.overlap_reasons),
                potential_collaboration=match.potential_collaboration,
                relevant_external_context=match.relevant_external_context,
                created_at=match.created_at,
                confirmed_at=match.confirmed_at,
            )
        )

    response.sort(key=lambda item: item.synergy_score, reverse=True)
    return response
