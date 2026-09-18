from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.connection import Base


class IntentEvidence(Base):
    __tablename__ = "intent_evidence"

    id = Column(Integer, primary_key=True, index=True)
    intent_brief_id = Column(
        Integer,
        ForeignKey("intent_briefs.id"),
        nullable=False,
        index=True,
    )
    source_title = Column(String, nullable=False)
    source_url = Column(Text, nullable=False)
    source_type = Column(String, nullable=True)
    signal_type = Column(String, nullable=True)
    excerpt = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
