from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text

from database.connection import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    niche = Column(String, nullable=False)
    problem = Column(Text, nullable=False)

    pain_score = Column(Float, nullable=False)
    worsening_score = Column(Float, nullable=False)
    purchasing_power_score = Column(Float, nullable=False)
    speed_score = Column(Float, nullable=False)

    overall_score = Column(Float, nullable=False)

    research_session_id = Column(
        Integer,
        ForeignKey("research_sessions.id"),
        nullable=True
    )