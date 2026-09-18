from html import escape
import re

from pydantic import BaseModel, Field
from reportlab.lib.colors import HexColor


DEFAULT_BRAND = {
    "brand_name": "NOVA",
    "tagline": "A practical guide built for real life.",
    "visual_direction": "Editorial, calm, useful, and confident. The design should feel like a premium practical guide rather than a corporate report.",
    "palette_name": "Quiet Contrast",
    "primary_color": "#17131F",
    "secondary_color": "#6F4BB8",
    "accent_color": "#A77BFF",
    "background_color": "#F8F6FB",
    "text_color": "#18151D",
    "heading_font": "Georgia",
    "body_font": "Arial",
    "cover_layout": "Editorial centered",
}


class BrandKitGeneration(BaseModel):
    brand_name: str = Field(description="A short brand or publisher name. Do not rename the product itself.")
    tagline: str = Field(description="A short supporting line for the product brand, without an exaggerated promise.")
    visual_direction: str = Field(description="A concise description of the visual mood, composition, and design language.")
    palette_name: str = Field(description="A memorable but professional name for the color palette.")
    primary_color: str = Field(description="Dark primary hex color such as #17131F.")
    secondary_color: str = Field(description="Secondary hex color such as #6F4BB8.")
    accent_color: str = Field(description="Accent hex color such as #A77BFF.")
    background_color: str = Field(description="Light background hex color suitable for a readable digital product.")
    text_color: str = Field(description="Dark readable text hex color.")
    heading_font: str = Field(description="A practical system font name suitable for headings, such as Georgia, Arial, or Trebuchet MS.")
    body_font: str = Field(description="A practical system font name suitable for body copy, such as Arial, Georgia, or Trebuchet MS.")
    cover_layout: str = Field(description="A concise description of the cover composition.")


def _hex(value: str, fallback: str) -> str:
    candidate = (value or "").strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", candidate):
        return fallback
    try:
        HexColor(candidate)
    except Exception:
        return fallback
    return candidate.upper()


def normalize_brand(data: BrandKitGeneration | dict) -> dict:
    source = data.model_dump() if isinstance(data, BrandKitGeneration) else data
    result = {**DEFAULT_BRAND, **source}
    for key in ["primary_color", "secondary_color", "accent_color", "background_color", "text_color"]:
        result[key] = _hex(result.get(key), DEFAULT_BRAND[key])
    result["brand_name"] = (result.get("brand_name") or "NOVA").strip()[:80]
    result["tagline"] = (result.get("tagline") or DEFAULT_BRAND["tagline"]).strip()[:180]
    result["visual_direction"] = (result.get("visual_direction") or DEFAULT_BRAND["visual_direction"]).strip()[:800]
    result["palette_name"] = (result.get("palette_name") or DEFAULT_BRAND["palette_name"]).strip()[:80]
    result["heading_font"] = (result.get("heading_font") or "Georgia").strip()[:60]
    result["body_font"] = (result.get("body_font") or "Arial").strip()[:60]
    result["cover_layout"] = (result.get("cover_layout") or DEFAULT_BRAND["cover_layout"]).strip()[:180]
    return result


def _svg_text(text: str, x: int, y: int, size: int, fill: str, font: str, weight: str = "400", anchor: str = "start") -> str:
    safe = escape(text)
    return f'<text x="{x}" y="{y}" fill="{fill}" font-family="{escape(font)}" font-size="{size}px" font-weight="{weight}" text-anchor="{anchor}">{safe}</text>'


def _wrap(text: str, max_chars: int) -> list[str]:
    words = (text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_cover_svg(title: str, subtitle: str, brand: dict) -> str:
    lines = _wrap(title, 28)[:4]
    subtitle_lines = _wrap(subtitle, 44)[:3]
    title_y = 410 - (len(lines) - 1) * 34
    title_parts = []
    for index, line in enumerate(lines):
        title_parts.append(_svg_text(line, 540, title_y + index * 68, 58, brand["text_color"], brand["heading_font"], "700", "middle"))
    subtitle_parts = []
    subtitle_y = title_y + len(lines) * 68 + 40
    for index, line in enumerate(subtitle_lines):
        subtitle_parts.append(_svg_text(line, 540, subtitle_y + index * 30, 22, brand["secondary_color"], brand["body_font"], "400", "middle"))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
<rect width="1080" height="1350" fill="{brand["background_color"]}"/>
<rect x="0" y="0" width="1080" height="28" fill="{brand["accent_color"]}"/>
<circle cx="88" cy="92" r="26" fill="{brand["secondary_color"]}"/>
{_svg_text(brand["brand_name"], 132, 103, 24, brand["primary_color"], brand["body_font"], "700")}
{_svg_text(brand["palette_name"], 992, 103, 14, brand["secondary_color"], brand["body_font"], "700", "end")}
<rect x="86" y="280" width="908" height="4" fill="{brand["accent_color"]}"/>
{''.join(title_parts)}
{''.join(subtitle_parts)}
<rect x="420" y="1050" width="240" height="3" fill="{brand["secondary_color"]}"/>
{_svg_text(brand["tagline"], 540, 1110, 18, brand["secondary_color"], brand["body_font"], "400", "middle")}
{_svg_text("Digital product edition", 540, 1210, 14, brand["text_color"], brand["body_font"], "400", "middle")}
</svg>'''


def build_social_card_svg(title: str, subtitle: str, brand: dict) -> str:
    lines = _wrap(title, 34)[:3]
    title_parts = [_svg_text(line, 90, 235 + i * 66, 48, brand["text_color"], brand["heading_font"], "700") for i, line in enumerate(lines)]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="{brand["background_color"]}"/>
<rect x="0" y="0" width="22" height="630" fill="{brand["secondary_color"]}"/>
{_svg_text(brand["brand_name"], 90, 90, 20, brand["secondary_color"], brand["body_font"], "700")}
{''.join(title_parts)}
{_svg_text((_wrap(subtitle, 62)[0] if subtitle else brand["tagline"]), 90, 465, 20, brand["secondary_color"], brand["body_font"], "400")}
<circle cx="1070" cy="520" r="90" fill="{brand["accent_color"]}" opacity="0.22"/>
<circle cx="1110" cy="470" r="48" fill="{brand["secondary_color"]}" opacity="0.22"/>
</svg>'''


def build_thumbnail_svg(title: str, brand: dict) -> str:
    lines = _wrap(title, 20)[:4]
    title_parts = [_svg_text(line, 300, 300 + i * 48, 38, brand["text_color"], brand["heading_font"], "700", "middle") for i, line in enumerate(lines)]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">
<rect width="600" height="600" rx="28" fill="{brand["background_color"]}"/>
<rect x="0" y="0" width="600" height="14" rx="7" fill="{brand["accent_color"]}"/>
{_svg_text(brand["brand_name"], 300, 110, 18, brand["secondary_color"], brand["body_font"], "700", "middle")}
{''.join(title_parts)}
<rect x="235" y="505" width="130" height="3" fill="{brand["secondary_color"]}"/>
</svg>'''


def build_assets(title: str, subtitle: str, brand: dict) -> dict:
    return {
        "cover_svg": build_cover_svg(title, subtitle, brand),
        "social_card_svg": build_social_card_svg(title, subtitle, brand),
        "thumbnail_svg": build_thumbnail_svg(title, brand),
    }


def generate_brand_kit(opportunity, transformation, summary, product_format: str) -> BrandKitGeneration:
    from google.genai import types
    from google.genai.errors import ServerError
    from ai_service import get_gemini_client

    client = get_gemini_client()
    prompt = f"""
You are NOVA's Brand Director.

Create a visual brand direction for a digital product. The product content and
positioning already exist. Your job is to create a coherent, professional
identity that can be used on the product cover, PDF interior, social preview,
and product thumbnail.

Do not rename or rewrite the product title. Do not invent research, statistics,
credentials, testimonials, guarantees, or factual claims.

The design should feel intentional, modern, readable, and human. It should not
look like a generic AI template. Favor restrained contrast, one strong accent,
and practical typography. Use only six-digit hex colors. Use common system font
names so the assets work without paid fonts or external downloads.

Return:
- brand_name
- tagline
- visual_direction
- palette_name
- primary_color
- secondary_color
- accent_color
- background_color
- text_color
- heading_font
- body_font
- cover_layout

PRODUCT FORMAT
{product_format}

PRODUCT TITLE
{summary.title}

PRODUCT SUBTITLE
{summary.subtitle}

PRODUCT ABOUT
{summary.about}

OPPORTUNITY
Industry: {opportunity.industry}
Niche: {opportunity.niche}
Problem: {opportunity.problem}

TRANSFORMATION
Before: {transformation.before_emotional_state}
After: {transformation.after_emotional_state}

Avoid em dashes and en dashes.
"""
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]
    last_error = None
    for model_name in models_to_try:
        try:
            print(f"Trying Gemini model for brand kit: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BrandKitGeneration,
                    temperature=0.65,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            if not response.parsed:
                raise RuntimeError(f"{model_name} returned an unparseable brand kit.")
            print(f"Successfully generated brand kit with: {model_name}")
            return response.parsed
        except ServerError as error:
            status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
            if status_code != 503:
                raise
            last_error = error
            print(f"{model_name} is temporarily unavailable. Trying the next model...")
        except RuntimeError as error:
            last_error = error
            print(f"{model_name} did not produce a valid brand kit. Trying the next model...")
    raise RuntimeError("Gemini could not produce a valid brand kit. Please try again.") from last_error
