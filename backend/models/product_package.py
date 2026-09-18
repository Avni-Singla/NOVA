from sqlalchemy import Column, Integer, String, Text, ForeignKey

from database.connection import Base


class ProductPackage(Base):
    __tablename__ = "product_packages"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        unique=True,
    )
    title = Column(String, nullable=False)
    subtitle = Column(Text, nullable=True)
    section_count = Column(Integer, nullable=False, default=0)
    total_word_count = Column(Integer, nullable=False, default=0)
    pdf_path = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft")
    generated_at = Column(String, nullable=True)
