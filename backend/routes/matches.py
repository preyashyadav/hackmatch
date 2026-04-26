from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models import Match


router = APIRouter()


class MatchMetRequest(BaseModel):
    met: bool


@router.post("/matches/{match_id}/met")
def mark_match_met(match_id: str, payload: MatchMetRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    match = db.query(Match).filter(Match.id == match_id).first()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if payload.met:
        match.status = "met"
        db.commit()

    return {"ok": True}
