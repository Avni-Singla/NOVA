from sqlalchemy import Column, Integer, String

from database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, nullable=False)
    format = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")