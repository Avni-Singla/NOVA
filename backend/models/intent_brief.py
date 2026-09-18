from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.connection import Base


class IntentBrief(Base):
    __tablename__ = "intent_briefs"

    id = Column(Integer, primary_key=True, index=True)
    problem_discovery_id = Column(
        Integer,
        ForeignKey("problem_discoveries.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    target_customer = Column(Text, nullable=True)
    problem_context = Column(Text, nullable=True)
    trigger = Column(Text, nullable=True)
    current_behavior = Column(Text, nullable=True)
    failed_alternatives = Column(Text, nullable=True)
    desired_outcome = Column(Text, nullable=True)
    constraints = Column(Text, nullable=True)
    objections = Column(Text, nullable=True)
    customer_language = Column(Text, nullable=True)
    existing_solutions = Column(Text, nullable=True)

    solution_gap = Column(Text, nullable=True)
    potential_solution = Column(Text, nullable=True)
    recommended_format = Column(String, nullable=True)
    why_format = Column(Text, nullable=True)

    validation_questions = Column(Text, nullable=True)
    evidence_confidence = Column(String, nullable=False, default="low")
    evidence_summary = Column(Text, nullable=True)

    source_count = Column(Integer, nullable=False, default=0)
    domain_count = Column(Integer, nullable=False, default=0)
    customer_signal_count = Column(Integer, nullable=False, default=0)
    solution_seeking_count = Column(Integer, nullable=False, default=0)
    spending_signal_count = Column(Integer, nullable=False, default=0)
    failed_attempt_count = Column(Integer, nullable=False, default=0)

    status = Column(String, nullable=False, default="investigated")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
