from sqlalchemy import Column, DateTime, Integer, String, Text
from datetime import datetime

from database.connection import Base


class ProblemDiscovery(Base):
    __tablename__ = "problem_discoveries"

    id = Column(Integer, primary_key=True, index=True)
    market_direction = Column(String, nullable=True)
    customer_group = Column(Text, nullable=False)
    situation = Column(Text, nullable=False)
    problem = Column(Text, nullable=False)
    trigger = Column(Text, nullable=True)
    current_behavior = Column(Text, nullable=True)
    initial_signal = Column(Text, nullable=True)
    investigation_reason = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="candidate")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
