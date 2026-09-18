from sqlalchemy import Column, Integer, String, Text, ForeignKey

from database.connection import Base


class ManuscriptSection(Base):
    __tablename__ = "manuscript_sections"

    id = Column(Integer, primary_key=True, index=True)

    section_id = Column(
        Integer,
        ForeignKey("sections.id"),
        nullable=False,
        unique=True,
    )

    content = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="draft")
