from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.connection import Base


class ReaderExperience(Base):
    __tablename__ = "reader_experiences"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    section_id = Column(
        Integer,
        ForeignKey("sections.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    intent_brief_id = Column(
        Integer,
        ForeignKey("intent_briefs.id"),
        nullable=True,
        index=True,
    )

    reader_job = Column(Text, nullable=True)
    reader_question = Column(Text, nullable=True)
    desired_reaction = Column(Text, nullable=True)
    experience_type = Column(String, nullable=True)
    visual_decision = Column(Text, nullable=True)
    interactive_element = Column(Text, nullable=True)
    evidence_anchor = Column(Text, nullable=True)
    claim_boundary = Column(Text, nullable=True)
    reader_action = Column(Text, nullable=True)
    transition_intent = Column(Text, nullable=True)
    avoid = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
