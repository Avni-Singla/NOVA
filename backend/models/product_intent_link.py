from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from database.connection import Base


class ProductIntentLink(Base):
    __tablename__ = "product_intent_links"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True, index=True)
    intent_brief_id = Column(Integer, ForeignKey("intent_briefs.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
