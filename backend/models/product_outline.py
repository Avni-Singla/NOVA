from sqlalchemy import Column, Integer, String, ForeignKey

from database.connection import Base


class ProductOutline(Base):
    __tablename__ = "product_outlines"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        unique=True,
    )
    status = Column(String, nullable=False, default="draft")