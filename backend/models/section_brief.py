from sqlalchemy import Column, Integer, String, Text, ForeignKey

from database.connection import Base


class SectionBrief(Base):
    __tablename__ = "section_briefs"

    id = Column(Integer, primary_key=True, index=True)

    section_id = Column(
        Integer,
        ForeignKey("sections.id"),
        nullable=False,
        unique=True,
    )

    objective = Column(Text, nullable=True)
    key_concepts = Column(Text, nullable=True)
    practical_steps = Column(Text, nullable=True)
    example_scenario = Column(Text, nullable=True)
    common_mistakes = Column(Text, nullable=True)
    reader_outcome = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="draft")
