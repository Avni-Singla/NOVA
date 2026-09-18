from sqlalchemy import Column, Integer, Text, ForeignKey
from database.connection import Base


class TransformationMap(Base):
    __tablename__ = "transformation_maps"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    before_emotional_state = Column(Text, nullable=True)
    before_core_fear = Column(Text, nullable=True)
    before_daily_experience = Column(Text, nullable=True)
    before_identity = Column(Text, nullable=True)

    after_emotional_state = Column(Text, nullable=True)
    after_core_fear = Column(Text, nullable=True)
    after_daily_experience = Column(Text, nullable=True)
    after_identity = Column(Text, nullable=True)