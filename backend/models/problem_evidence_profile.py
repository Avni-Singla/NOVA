from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.connection import Base


class ProblemEvidenceProfile(Base):
    __tablename__ = "problem_evidence_profiles"

    id = Column(Integer, primary_key=True, index=True)
    problem_discovery_id = Column(Integer, ForeignKey("problem_discoveries.id"), nullable=False, unique=True, index=True)
    pain_summary = Column(Text, nullable=True)
    economic_consequence = Column(Text, nullable=True)
    existing_attempts = Column(Text, nullable=True)
    solution_seeking = Column(Text, nullable=True)
    spending_signal = Column(Text, nullable=True)
    repeated_pattern = Column(Text, nullable=True)
    evidence_confidence = Column(String, nullable=False, default="low")
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
