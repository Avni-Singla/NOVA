from sqlalchemy import Column, Integer, Text, ForeignKey
from database.connection import Base


class ProductSummary(Base):
    __tablename__ = "product_summaries"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        unique=True,
        nullable=False,
    )

    title = Column(Text, nullable=True)
    subtitle = Column(Text, nullable=True)
    about = Column(Text, nullable=True)
    what_youll_learn = Column(Text, nullable=True)

    estimated_reading_time = Column(
        Integer,
        nullable=True,
    )

    section_count = Column(
        Integer,
        nullable=True,
    )

    bonus_materials = Column(Text, nullable=True)