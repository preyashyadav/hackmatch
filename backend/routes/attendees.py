from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models import Attendee


router = APIRouter()


class AttendeeResponse(BaseModel):
    id: str
    name: str
    contact_email: str
    agent_email: str
    project_idea: str
    looking_for: str
    theme_alignment_score: float
    created_at: datetime


@router.get("/attendees/{attendee_id}", response_model=AttendeeResponse)
def get_attendee(attendee_id: str, db: Session = Depends(get_db)) -> AttendeeResponse:
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")

    return AttendeeResponse(
        id=attendee.id,
        name=attendee.name,
        contact_email=attendee.contact_email,
        agent_email=attendee.agent_email,
        project_idea=attendee.project_idea,
        looking_for=attendee.looking_for,
        theme_alignment_score=attendee.theme_alignment_score,
        created_at=attendee.created_at,
    )
