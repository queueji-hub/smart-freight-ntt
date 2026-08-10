"""User Manual PDF generator with Thai font support.

Renders USER_MANUAL.md to A4 PDF.
Tries to use DejaVuSans (available on Streamlit Cloud Linux), falls back
to Helvetica if not found.
"""
import re
from pathlib import Path
from datetime import datetime
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import COMPANY, OUTPUT_DIR, BASE_DIR


BRAND_BLUE = colors.HexColor("#1F4E9E")
BRAND_GOLD = colors.HexColor("#C9A227")
HEADER_GREY = colors.HexColor("#9CA3AF")
CODE_BG = colors.HexColor("#F3F4F6")


# ===== Font registration with fallback =====

_FONT_REG = None
_FONT_BOLD_REG = None


def _register_thai_font() -> tuple:
    """Try to register a Unicode font that supports Thai. Returns (regular, bold) names."""
    global _FONT_REG, _FONT_BOLD_REG
    if _FONT_REG is not None:
        return _FONT_REG, _FONT_BOLD_REG
    
    # Try common font paths (order: bundled → Linux → fallback)
    font_candidates = [
        # Bundled Thai font (if user added to assets/fonts/)
        (BASE_DIR / "assets" / "fonts" / "Sarabun-Regular.ttf",
         BASE_DIR / "assets" / "fonts" / "Sarabun-Bold.ttf",
         "Sarabun"),
        # DejaVu (Linux, Streamlit Cloud)
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
         Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
         "DejaVuSans"),
        # Liberation Sans (alternative Linux)
        (Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
         Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
         "LiberationSans"),
        # macOS
        (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
         Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
         "ArialUnicode"),
        # Windows (dev only)
        (Path("C:/Windows/Fonts/tahoma.ttf"),
         Path("C:/Windows/Fonts/tahomabd.ttf"),
         "Tahoma"),
    ]
    
    for reg_path, bold_path, name in font_candidates:
        try:
            if reg_path.exists():
                pdfmetrics.registerFont(TTFont(name, str(reg_path)))
                bold_name = name + "-Bold"
                if bold_path.exists() and bold_path != reg_path:
                    pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
                else:
                    bold_name = name  # use same font
                _FONT_REG = name
                _FONT_BOLD_REG = bold_name
                return name, bold_name
        except Exception:
            continue
    
    # Final fallback — built-in (Thai will show as boxes)
    _FONT_REG = "Helvetica"
    _FONT_BOLD_REG = "Helvetica-Bold"
    return _FONT_REG, _FONT_BOLD_REG


def _styles():
    font, font_b = _register_thai_font()
    base = getSampleStyleSheet()
    
    return {
        "title": ParagraphStyle("ttl", parent=base["Normal"],
            fontName=font_b, fontSize=24, textColor=BRAND_BLUE,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=10, leading=28),
        "subtitle": ParagraphStyle("sub", parent=base["Normal"],
            fontName=font, fontSize=12, textColor=colors.grey,
            alignment=TA_CENTER, spaceAfter=20, leading=15),
        "h1": ParagraphStyle("h1", parent=base["Normal"],
            fontName=font_b, fontSize=18, textColor=BRAND_BLUE,
            spaceBefore=14, spaceAfter=8, leading=22),
        "h2": ParagraphStyle("h2", parent=base["Normal"],
            fontName=font_b, fontSize=14, textColor=BRAND_BLUE,
            spaceBefore=10, spaceAfter=6, leading=18),
        "h3": ParagraphStyle("h3", parent=base["Normal"],
            fontName=font_b, fontSize=11, textColor=colors.HexColor("#374151"),
            spaceBefore=8, spaceAfter=4, leading=14),
        "h4": ParagraphStyle("h4", parent=base["Normal"],
            fontName=font_b, fontSize=10, textColor=colors.HexColor("#4B5563"),
            spaceBefore=6, spaceAfter=3, leading=13),
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontName=font, fontSize=10, leading=14, spaceAfter=4,
            alignment=TA_LEFT),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
            fontName=font, fontSize=10, leading=14, leftIndent=18,
            bulletIndent=6, spaceAfter=2),
        "code": ParagraphStyle("code", parent=base["Normal"],
            fontName="Courier", fontSize=8.5,
            backColor=CODE_BG, leftIndent=10, rightIndent=10,
            leading=11, spaceBefore=4, spaceAfter=6,
            borderColor=colors.HexColor("#D1D5DB"),
            borderWidth=0.5, borderPadding=4),
        "quote": ParagraphStyle("quote", parent=base["Normal"],
            fontName=font, fontSize=10, textColor=colors.HexColor("#6B7280"),
            leftIndent=20, leading=14, spaceAfter=4,
            borderColor=BRAND_GOLD, borderWidth=0,
            borderPadding=4, backColor=colors.HexColor("#FEF3C7")),
        "small": ParagraphStyle("small", parent=base["Normal"],
            fontName=font, fontSize=9, textColor=colors.grey,
            alignment=TA_CENTER, leading=11),
    }


def _escape(text: str) -> str:
    """Escape XML special chars for reportlab Paragraph (keep <b> and <i> intact)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_inline(text: str) -> str:
    """Convert inline markdown to reportlab markup."""
    text = _escape(text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    # Inline code: `code`
    text = re.sub(r"`([^`]+?)`",
                   r'<font name="Courier" backColor="#F3F4F6">\1</font>', text)
    # Links: [text](url) → just show text
    text = re.sub(r"\[([^\]]+?)\]\([^)]+?\)", r"\1", text)
    return text


def _parse_table(lines: List[str], styles) -> Table:
    """Parse a markdown table and return reportlab Table."""
    if len(lines) < 2:
        return None
    
    def split_row(line):
        # Strip leading/trailing |, then split
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [c.strip() for c in s.split("|")]
    
    headers = split_row(lines[0])
    body = [split_row(l) for l in lines[2:]]  # skip separator line
    
    if not headers:
        return None
    
    data = [[Paragraph(f"<b>{_md_inline(h)}</b>", styles["body"])
             for h in headers]]
    for row in body:
        # Pad row to match header length
        while len(row) < len(headers):
            row.append("")
        data.append([Paragraph(_md_inline(c), styles["body"]) for c in row[:len(headers)]])
    
    n_cols = len(headers)
    available_width = 180  # mm (A4 minus margins)
    col_w = [available_width / n_cols * mm] * n_cols
    
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BRAND_BLUE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#9CA3AF")),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1),
         [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    return tbl


def _parse_markdown(md_text: str, styles) -> List:
    """Parse markdown into reportlab flowables."""
    flowables = []
    lines = md_text.split("\n")
    i = 0
    
    in_code = False
    code_buf = []
    
    while i < len(lines):
        line = lines[i]
        
        # Code block
        if line.strip().startswith("```"):
            if in_code:
                # End of code block
                code_text = "\n".join(code_buf).replace("<", "&lt;").replace(">", "&gt;")
                flowables.append(Paragraph(
                    code_text.replace("\n", "<br/>"), styles["code"]))
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        
        if in_code:
            code_buf.append(line)
            i += 1
            continue
        
        # Headings
        if line.startswith("# "):
            flowables.append(Spacer(1, 4*mm))
            flowables.append(Paragraph(_md_inline(line[2:]), styles["h1"]))
        elif line.startswith("## "):
            flowables.append(Paragraph(_md_inline(line[3:]), styles["h2"]))
        elif line.startswith("### "):
            flowables.append(Paragraph(_md_inline(line[4:]), styles["h3"]))
        elif line.startswith("#### "):
            flowables.append(Paragraph(_md_inline(line[5:]), styles["h4"]))
        
        # Horizontal rule
        elif line.strip() == "---":
            flowables.append(Spacer(1, 3*mm))
        
        # Blockquote
        elif line.startswith("> "):
            flowables.append(Paragraph(_md_inline(line[2:]), styles["quote"]))
        
        # Bullet list
        elif re.match(r"^[\-\*] ", line):
            content = line[2:]
            flowables.append(Paragraph("• " + _md_inline(content),
                                         styles["bullet"]))
        
        # Numbered list
        elif re.match(r"^\d+\. ", line):
            content = re.sub(r"^\d+\. ", "", line)
            flowables.append(Paragraph(_md_inline(content),
                                         styles["bullet"]))
        
        # Table
        elif line.strip().startswith("|") and "|" in line.strip()[1:]:
            # Collect all consecutive table lines
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            tbl = _parse_table(table_lines, styles)
            if tbl is not None:
                flowables.append(Spacer(1, 2*mm))
                flowables.append(tbl)
                flowables.append(Spacer(1, 2*mm))
            continue  # skip i+=1 below since we already advanced
        
        # Empty line
        elif not line.strip():
            pass
        
        # Paragraph
        else:
            flowables.append(Paragraph(_md_inline(line), styles["body"]))
        
        i += 1
    
    return flowables


def _cover_page(styles) -> List:
    """Generate cover page flowables."""
    flowables = []
    
    flowables.append(Spacer(1, 40*mm))
    
    # Logo
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        try:
            from reportlab.lib.utils import ImageReader
            ir = ImageReader(logo_path)
            iw, ih = ir.getSize()
            scale = min(60*mm / iw, 40*mm / ih)
            logo_tbl = Table([[Image(logo_path, width=iw*scale, height=ih*scale)]],
                              colWidths=[180*mm])
            logo_tbl.setStyle(TableStyle([
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ]))
            flowables.append(logo_tbl)
            flowables.append(Spacer(1, 10*mm))
        except Exception:
            pass
    
    flowables.append(Paragraph("📘 USER MANUAL", styles["title"]))
    flowables.append(Paragraph("FreightFlow NTT", styles["subtitle"]))
    flowables.append(Spacer(1, 4*mm))
    flowables.append(Paragraph(
        "Freight Forwarding Operating System", styles["subtitle"]))
    
    flowables.append(Spacer(1, 60*mm))
    
    # Company block
    flowables.append(Paragraph(
        f"<b>{COMPANY['name']}</b>", styles["h3"]))
    flowables.append(Paragraph(
        f"{COMPANY['address_line1']}", styles["small"]))
    flowables.append(Paragraph(
        f"{COMPANY['address_line2']} {COMPANY['address_line3']}",
        styles["small"]))
    flowables.append(Paragraph(
        f"Tel: {COMPANY['tel']} · Email: {COMPANY['email']}",
        styles["small"]))
    
    flowables.append(Spacer(1, 10*mm))
    flowables.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y')}",
        styles["small"]))
    flowables.append(Paragraph(
        "Version 1.0", styles["small"]))
    
    flowables.append(PageBreak())
    return flowables


def _page_decoration(canvas, doc):
    """Footer with page number on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    
    # Footer
    canvas.drawString(15*mm, 10*mm, "FreightFlow NTT — User Manual")
    canvas.drawRightString(A4[0] - 15*mm, 10*mm, f"Page {doc.page}")
    
    # Top line
    canvas.setStrokeColor(BRAND_BLUE)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, A4[1] - 12*mm, A4[0] - 15*mm, A4[1] - 12*mm)
    
    canvas.restoreState()


def generate_manual_pdf(output_path: str = None) -> str:
    """Generate User Manual PDF from USER_MANUAL.md."""
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / "Smart_Freight_NTT_Manual.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Read markdown
    md_path = BASE_DIR / "USER_MANUAL.md"
    if not md_path.exists():
        raise FileNotFoundError(f"USER_MANUAL.md not found at {md_path}")
    
    md_text = md_path.read_text(encoding="utf-8")
    
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title="FreightFlow NTT - User Manual",
        author=COMPANY["name"],
    )
    
    styles = _styles()
    story = []
    
    # Cover page
    story.extend(_cover_page(styles))
    
    # Content (skip the first H1 since we have cover)
    # Remove the very first H1 line if it matches
    md_lines = md_text.split("\n", 1)
    if md_lines and md_lines[0].startswith("# "):
        md_text = md_lines[1] if len(md_lines) > 1 else ""
    
    story.extend(_parse_markdown(md_text, styles))
    
    doc.build(story, onFirstPage=_page_decoration,
                onLaterPages=_page_decoration)
    return output_path
