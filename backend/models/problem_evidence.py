from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.connection import Base


class ProblemEvidence(Base):
    __tablename__ = "problem_evidence"

    id = Column(Integer, primary_key=True, index=True)
    problem_discovery_id = Column(Integer, ForeignKey("problem_discoveries.id"), nullable=False, index=True)
    source_title = Column(String, nullable=False)
    source_url = Column(Text, nullable=False)
    source_type = Column(String, nullable=True)
    signal_type = Column(String, nullable=True)
    excerpt = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
