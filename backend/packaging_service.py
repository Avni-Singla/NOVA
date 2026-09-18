from html import escape
from pathlib import Path
import re
from datetime import datetime

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    PageBreak,
    Spacer,
    KeepTogether,
    HRFlowable,
)
from reportlab.platypus.tableofcontents import TableOfContents


def _clean_text(value: str | None) -> str:
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("—", "-").replace("–", "-").replace("‑", "-")
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = text.replace("\u00a0", " ")
    return text.strip()


def _register_font() -> str:
    candidates = [
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("NOVASans", str(path)))
                return "NOVASans"
            except Exception:
                pass
    return "Helvetica"


class NovaDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        self.addPageTemplates([
            PageTemplate(id="main", frames=frame, onPage=self._draw_page)
        ])

    def _draw_page(self, canvas, doc):
        page = canvas.getPageNumber()
        if page <= 1:
            return
        canvas.saveState()
        canvas.setFont(self.font_name, 8)
        canvas.setFillColorRGB(0.40, 0.40, 0.45)
        canvas.drawCentredString(A4[0] / 2, 12 * mm, str(page - 1))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            if style == "NOVASectionTitle":
                text = flowable.getPlainText()
                self.notify('TOCEntry', (0, text, self.page))


def _paragraphs_from_content(content: str, styles: dict):
    cleaned = _clean_text(content)
    if not cleaned:
        return []

    lines = cleaned.split("\n")
    flowables = []
    paragraph_lines = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text = " ".join(line.strip() for line in paragraph_lines if line.strip())
        if text:
            flowables.append(Paragraph(escape(text).replace("\n", "<br/>"), styles["body"]))
            flowables.append(Spacer(1, 4.5 * mm))
        paragraph_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue

        if line.startswith("# "):
            flush_paragraph()
            continue
        if line.startswith("## "):
            flush_paragraph()
            heading = escape(line[3:].strip())
            flowables.append(Paragraph(heading, styles["subheading"]))
            flowables.append(Spacer(1, 2 * mm))
            continue
        if re.match(r"^(?:[-*]|\d+\.)\s+", line):
            flush_paragraph()
            bullet_text = re.sub(r"^(?:[-*]|\d+\.)\s+", "", line)
            flowables.append(Paragraph("• " + escape(bullet_text), styles["bullet"]))
            continue

        paragraph_lines.append(line)

    flush_paragraph()
    return flowables


def generate_product_pdf(
    output_path: str,
    title: str,
    subtitle: str,
    about: str,
    bonus_materials: str,
    sections: list[tuple[int, str, str]],
    branding: dict | None = None,
):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_font()
    branding = branding or {}

    def safe_color(value: str | None, fallback: str):
        try:
            return HexColor(value) if value else HexColor(fallback)
        except Exception:
            return HexColor(fallback)

    primary_color = safe_color(branding.get("primary_color"), "#17131F")
    secondary_color = safe_color(branding.get("secondary_color"), "#6F4BB8")
    accent_color = safe_color(branding.get("accent_color"), "#A77BFF")
    background_color = safe_color(branding.get("background_color"), "#F8F6FB")
    text_color = safe_color(branding.get("text_color"), "#18151D")
    brand_name = _clean_text(branding.get("brand_name")) or "NOVA"
    tagline = _clean_text(branding.get("tagline")) or "A practical digital guide"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="NOVACoverTitle",
        fontName=font_name,
        fontSize=28,
        leading=34,
        alignment=TA_CENTER,
        spaceAfter=10 * mm,
    ))
    styles.add(ParagraphStyle(
        name="NOVACoverSubtitle",
        fontName=font_name,
        fontSize=13,
        leading=19,
        alignment=TA_CENTER,
        textColor=secondary_color,
        spaceAfter=16 * mm,
    ))
    styles.add(ParagraphStyle(
        name="NOVAIntro",
        fontName=font_name,
        fontSize=11,
        leading=17,
        alignment=TA_CENTER,
        textColor=text_color,
    ))
    styles.add(ParagraphStyle(
        name="NOVATocTitle",
        fontName=font_name,
        fontSize=22,
        leading=28,
        spaceAfter=8 * mm,
    ))
    styles.add(ParagraphStyle(
        name="NOVASectionTitle",
        fontName=font_name,
        fontSize=21,
        leading=27,
        spaceBefore=4 * mm,
        spaceAfter=7 * mm,
        textColor=primary_color,
    ))
    styles.add(ParagraphStyle(
        name="NOVASectionNumber",
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=secondary_color,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name="body",
        fontName=font_name,
        fontSize=10.5,
        leading=17,
        alignment=TA_LEFT,
        textColor=text_color,
    ))
    styles.add(ParagraphStyle(
        name="subheading",
        fontName=font_name,
        fontSize=14,
        leading=19,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        textColor=primary_color,
    ))
    styles.add(ParagraphStyle(
        name="bullet",
        fontName=font_name,
        fontSize=10.2,
        leading=16,
        leftIndent=6 * mm,
        firstLineIndent=-4 * mm,
        spaceAfter=1.5 * mm,
        textColor=text_color,
    ))

    doc = NovaDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=_clean_text(title) or "NOVA Product",
        author="NOVA",
    )
    doc.font_name = font_name

    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle(
        name="NOVATocEntry",
        fontName=font_name,
        fontSize=10.5,
        leading=17,
        leftIndent=0,
        firstLineIndent=0,
        spaceAfter=3 * mm,
    )]

    story = []
    safe_title = escape(_clean_text(title) or "Untitled Product")
    safe_subtitle = escape(_clean_text(subtitle))
    safe_about = escape(_clean_text(about))

    story.append(Spacer(1, 20 * mm))
    story.append(HRFlowable(width="100%", thickness=10, hAlign="CENTER", color=accent_color))
    story.append(Spacer(1, 28 * mm))
    story.append(Paragraph(escape(brand_name), ParagraphStyle(
        "NOVAWordmark", fontName=font_name, fontSize=10, leading=12,
        alignment=TA_CENTER, textColor=secondary_color, spaceAfter=8 * mm,
    )))
    story.append(Paragraph(safe_title, styles["NOVACoverTitle"]))
    if safe_subtitle:
        story.append(Paragraph(safe_subtitle, styles["NOVACoverSubtitle"]))
    if safe_about:
        story.append(Paragraph(safe_about, styles["NOVAIntro"]))
    story.append(Spacer(1, 32 * mm))
    story.append(HRFlowable(width="35%", thickness=0.8, hAlign="CENTER", color=accent_color))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(escape(tagline), ParagraphStyle(
        "NOVAFooter", fontName=font_name, fontSize=9, leading=12,
        alignment=TA_CENTER, textColor=secondary_color,
    )))

    story.append(PageBreak())
    story.append(Paragraph("Contents", styles["NOVATocTitle"]))
    story.append(toc)
    story.append(PageBreak())

    for position, section_title, content in sections:
        story.append(Paragraph(f"SECTION {position:02d}", styles["NOVASectionNumber"]))
        story.append(Paragraph(escape(_clean_text(section_title)), styles["NOVASectionTitle"]))
        story.extend(_paragraphs_from_content(content, styles))
        story.append(PageBreak())

    if _clean_text(bonus_materials):
        story.append(Paragraph("Bonus Materials", styles["NOVASectionTitle"]))
        story.extend(_paragraphs_from_content(bonus_materials, styles))

    doc.multiBuild(story)
    return path
