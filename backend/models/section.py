from sqlalchemy import Column, Integer, String, Text, ForeignKey

from database.connection import Base


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)

    outline_id = Column(
        Integer,
        ForeignKey("product_outlines.id"),
        nullable=False,
    )

    position = Column(Integer, nullable=False)

    title = Column(String, nullable=False)

    purpose = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="draft")