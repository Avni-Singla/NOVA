from sqlalchemy import Column, Integer, String, Text, ForeignKey

from database.connection import Base


class ContentBlueprint(Base):
    __tablename__ = "content_blueprints"

    id = Column(Integer, primary_key=True, index=True)

    section_id = Column(
        Integer,
        ForeignKey("sections.id"),
        nullable=False,
        unique=True,
    )

    hook_angle = Column(Text, nullable=True)
    core_explanation = Column(Text, nullable=True)
    supporting_points = Column(Text, nullable=True)
    reader_action = Column(Text, nullable=True)
    example_scenario = Column(Text, nullable=True)
    misconception_or_objection = Column(Text, nullable=True)
    transition_to_next = Column(Text, nullable=True)
    avoid = Column(Text, nullable=True)
    target_word_count = Column(Integer, nullable=True)

    status = Column(String, nullable=False, default="draft")
