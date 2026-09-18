from sqlalchemy import Column, Integer, String, ForeignKey
from database.connection import Base


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    mode = Column(String, nullable=False)
    status = Column(String, nullable=False, default="completed")