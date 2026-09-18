from branding_service import build_assets, normalize_brand


brand = normalize_brand({
    "brand_name": "NOVA Studio",
    "tagline": "Make useful ideas easier to ship.",
    "palette_name": "Quiet Contrast",
    "primary_color": "#111111",
    "secondary_color": "#6633AA",
    "accent_color": "#AA77FF",
    "background_color": "#F8F6FB",
    "text_color": "#18151D",
    "heading_font": "Georgia",
    "body_font": "Arial",
    "cover_layout": "Editorial centered",
})

assets = build_assets(
    "The Single-Income Budgeting Guide",
    "A practical method for making one paycheck last.",
    brand,
)

assert assets["cover_svg"].startswith("<svg")
assert assets["social_card_svg"].startswith("<svg")
assert assets["thumbnail_svg"].startswith("<svg")
assert "Single-Income" in assets["cover_svg"]
assert "Budgeting" in assets["cover_svg"]
assert brand["accent_color"] == "#AA77FF"

print("Branding asset test passed!")
print("Cover SVG characters:", len(assets["cover_svg"]))
print("Social SVG characters:", len(assets["social_card_svg"]))
print("Thumbnail SVG characters:", len(assets["thumbnail_svg"]))
