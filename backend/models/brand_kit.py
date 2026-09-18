from sqlalchemy import Column, Integer, String, Text, ForeignKey

from database.connection import Base


class BrandKit(Base):
    __tablename__ = "brand_kits"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)

    brand_name = Column(String, nullable=True)
    tagline = Column(Text, nullable=True)
    visual_direction = Column(Text, nullable=True)
    palette_name = Column(String, nullable=True)
    primary_color = Column(String, nullable=False, default="#17131F")
    secondary_color = Column(String, nullable=False, default="#6F4BB8")
    accent_color = Column(String, nullable=False, default="#A77BFF")
    background_color = Column(String, nullable=False, default="#F8F6FB")
    text_color = Column(String, nullable=False, default="#18151D")
    heading_font = Column(String, nullable=False, default="Georgia")
    body_font = Column(String, nullable=False, default="Arial")
    cover_layout = Column(String, nullable=True)
    cover_svg = Column(Text, nullable=True)
    social_card_svg = Column(Text, nullable=True)
    thumbnail_svg = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft")
