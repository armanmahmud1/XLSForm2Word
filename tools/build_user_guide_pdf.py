"""Render docs/USER_GUIDE.md into the distributable README.pdf."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.version import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    DESCRIPTION,
    WEBSITE,
)

GUIDE_SOURCE = ROOT / "docs" / "USER_GUIDE.md"
OUTPUT = ROOT / "README.pdf"
GREEN = colors.HexColor("#2E7D32")
DARK_GREEN = colors.HexColor("#1B5E20")
GREY = colors.HexColor("#6B7280")
TEXT = colors.HexColor("#1F2937")
LIGHT_GREY = colors.HexColor("#9CA3AF")


def _register_fonts() -> tuple[str, str, str, str]:
    windows_fonts = Path(r"C:\Windows\Fonts")
    candidates = {
        "light": [windows_fonts / "calibril.ttf", windows_fonts / "arial.ttf"],
        "regular": [windows_fonts / "calibri.ttf", windows_fonts / "arial.ttf"],
        "bold": [windows_fonts / "calibrib.ttf", windows_fonts / "arialbd.ttf"],
        "bolditalic": [
            windows_fonts / "calibriz.ttf",
            windows_fonts / "arialbi.ttf",
        ],
    }
    registered: dict[str, str] = {}
    for key, paths in candidates.items():
        for path in paths:
            if not path.exists():
                continue
            try:
                name = f"XLS2W-{key.title()}"
                pdfmetrics.registerFont(TTFont(name, str(path)))
                registered[key] = name
                break
            except (OSError, TTFError):
                registered[key] = "Helvetica"
                break
        registered.setdefault(key, "Helvetica")
    pdfmetrics.registerFontFamily(
        registered["regular"],
        normal=registered["regular"],
        bold=registered["bold"],
        italic=registered["regular"],
        boldItalic=registered["bolditalic"],
    )
    return (
        registered["light"],
        registered["regular"],
        registered["bold"],
        registered["bolditalic"],
    )


def _inline_markup(text: str) -> str:
    escaped = escape(text.strip())
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<link href="\2" color="#2E7D32">\1</link>',
        escaped,
    )
    return escaped


def _build_styles(
    light: str,
    regular: str,
    bold: str,
) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=light,
            fontSize=28,
            leading=34,
            textColor=DARK_GREEN,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName=regular,
            fontSize=11,
            leading=16,
            textColor=GREY,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=bold,
            fontSize=16,
            leading=20,
            textColor=GREEN,
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName=bold,
            fontSize=12,
            leading=16,
            textColor=TEXT,
            spaceBefore=9,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=10,
            leading=15,
            textColor=TEXT,
            alignment=TA_LEFT,
            spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=10,
            leading=14,
            textColor=TEXT,
            leftIndent=14,
            bulletIndent=4,
            spaceAfter=3,
        ),
        "number": ParagraphStyle(
            "Number",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=10,
            leading=14,
            textColor=TEXT,
            leftIndent=20,
            bulletIndent=4,
            spaceAfter=3,
        ),
    }


def _story(md_text: str, styles: dict[str, ParagraphStyle]) -> list[object]:
    story: list[object] = []
    icon = ROOT / "assets" / "icon.png"
    if icon.exists():
        story.append(Spacer(1, 2.2 * cm))
        image = Image(str(icon), width=3.2 * cm, height=3.2 * cm)
        image.hAlign = "CENTER"
        story.append(image)
        story.append(Spacer(1, 0.5 * cm))
    else:
        story.append(Spacer(1, 4 * cm))

    story.append(Paragraph(APP_NAME, styles["title"]))
    story.append(Paragraph("User Guide", styles["subtitle"]))
    story.append(Paragraph(_inline_markup(DESCRIPTION), styles["subtitle"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            _inline_markup(f"Version {APP_VERSION}  |  {AUTHOR}  |  {WEBSITE}"),
            styles["subtitle"],
        )
    )
    story.append(PageBreak())

    lines = md_text.splitlines()
    paragraph_buffer: list[str] = []
    in_code = False
    first_heading_skipped = False

    def flush_paragraph() -> None:
        if not paragraph_buffer:
            return
        text = " ".join(part.strip() for part in paragraph_buffer).strip()
        paragraph_buffer.clear()
        if text:
            story.append(Paragraph(_inline_markup(text), styles["body"]))

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            in_code = not in_code
            continue
        if in_code:
            if stripped:
                story.append(
                    Paragraph(
                        f"<font name='Courier'>{escape(stripped)}</font>",
                        styles["body"],
                    )
                )
            continue

        if not stripped:
            flush_paragraph()
            story.append(Spacer(1, 2))
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            heading = stripped[2:].strip()
            if not first_heading_skipped:
                first_heading_skipped = True
                continue
            story.append(Paragraph(_inline_markup(heading), styles["h2"]))
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(_inline_markup(stripped[3:]), styles["h2"]))
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(_inline_markup(stripped[4:]), styles["h3"]))
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            story.append(
                Paragraph(
                    _inline_markup(bullet.group(1)),
                    styles["bullet"],
                    bulletText="•",
                )
            )
            continue

        numbered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if numbered:
            flush_paragraph()
            number = stripped.split(".", 1)[0]
            story.append(
                Paragraph(
                    _inline_markup(numbered.group(1)),
                    styles["number"],
                    bulletText=f"{number}.",
                )
            )
            continue

        paragraph_buffer.append(stripped)

    flush_paragraph()
    return story


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(LIGHT_GREY)
    left = f"{APP_NAME} v{APP_VERSION}"
    website = WEBSITE.replace("https://", "").replace("http://", "")
    canvas.drawString(2 * cm, 1.15 * cm, left)
    canvas.drawRightString(
        A4[0] - 2 * cm,
        1.15 * cm,
        f"{AUTHOR} | {website}  |  Page {document.page}",
    )
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(2 * cm, 1.55 * cm, A4[0] - 2 * cm, 1.55 * cm)
    canvas.restoreState()


def build() -> Path:
    md_text = GUIDE_SOURCE.read_text(encoding="utf-8")
    light, regular, bold, _ = _register_fonts()
    styles = _build_styles(light, regular, bold)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"{APP_NAME} User Guide",
        author=AUTHOR,
        subject=DESCRIPTION,
        creator=f"{APP_NAME} v{APP_VERSION}",
    )
    document.build(
        _story(md_text, styles),
        onFirstPage=_footer,
        onLaterPages=_footer,
    )
    return OUTPUT


def main() -> None:
    output = build()
    print(f"Created {output}")


if __name__ == "__main__":
    main()
