import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text

from db import Base


class Attendee(Base):
    __tablename__ = "attendees"

    id = Column(String(12), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    agent_email = Column(String, nullable=False, unique=True)
    inbox_id = Column(String, nullable=False, unique=True)
    project_idea = Column(Text, nullable=False)
    looking_for = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)
    theme_alignment_score = Column(Float, nullable=False, default=0.0)
    nia_source_id = Column(String, nullable=True)
    is_persona = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Match(Base):
    __tablename__ = "matches"

    id = Column(String(12), primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    attendee_a_id = Column(String(12), ForeignKey("attendees.id"), nullable=False)
    attendee_b_id = Column(String(12), ForeignKey("attendees.id"), nullable=False)
    proposer_attendee_id = Column(String(12), ForeignKey("attendees.id"), nullable=False)
    pair_key = Column(String(25), nullable=False, unique=True)
    status = Column(String, nullable=False)
    synergy_score = Column(Float, nullable=False)
    theme_alignment_score = Column(Float, nullable=False)
    theme_alignment_a_score = Column(Float, nullable=False)
    theme_alignment_b_score = Column(Float, nullable=False)
    overlap_reasons = Column(Text, nullable=False)
    potential_collaboration = Column(Text, nullable=False)
    relevant_external_context = Column(Text, nullable=False, default="")
    agent_conversation = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
