"""A4 Quotation PDF generator (matches Nattayaraat layout)."""
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

# Brand colors (matching the sample PDF)
BRAND_BLUE = colors.HexColor("#1F4E9E")
BRAND_GOLD = colors.HexColor("#C9A227")
HEADER_GREY = colors.HexColor("#9CA3AF")


def _format_date(d) -> str:
    """Format date as DD-MM-YY (e.g. 12-05-26)."""
    if d is None:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return d
    return d.strftime("%d-%m-%y")


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle(
            "company", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=18, textColor=BRAND_GOLD,
            alignment=TA_LEFT, spaceAfter=10, leading=22,
        ),
        "company_addr": ParagraphStyle(
            "company_addr", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, textColor=BRAND_BLUE,
            alignment=TA_LEFT, leading=13, spaceBefore=4,
        ),
        "title": ParagraphStyle(
            "title", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=14, textColor=BRAND_BLUE,
            alignment=TA_CENTER, spaceBefore=8, spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "label", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=9, textColor=colors.black,
        ),
        "value": ParagraphStyle(
            "value", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, textColor=colors.black,
        ),
        "subject": ParagraphStyle(
            "subject", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=10,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, leading=12, alignment=TA_LEFT,
        ),
        "tc_heading": ParagraphStyle(
            "tc_heading", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=10,
            textColor=colors.black, spaceBefore=4, spaceAfter=4,
        ),
        "tc_item": ParagraphStyle(
            "tc_item", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, leading=12,
            leftIndent=20, bulletIndent=8,
        ),
    }


def _build_header(styles) -> Table:
    """Header: logo on left, company name + address on right."""
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        # Preserve aspect ratio: fit within 45mm x 28mm box
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(logo_path)
        iw, ih = img_reader.getSize()
        max_w, max_h = 45*mm, 28*mm
        scale = min(max_w / iw, max_h / ih)
        logo = Image(logo_path, width=iw*scale, height=ih*scale)
    else:
        logo = Paragraph("<b>[LOGO]</b>", styles["body"])
    
    addr_html = (
        f'<font size="9" color="#1F4E9E">'
        f'{COMPANY["address_line1"]}<br/>'
        f'{COMPANY["address_line2"]}<br/>'
        f'{COMPANY["address_line3"]} Tax ID {COMPANY["tax_id"]} '
        f'Tel {COMPANY["tel"]}<br/>'
        f'Email:{COMPANY["email"]}'
        f'</font>'
    )
    company_block = [
        Paragraph(COMPANY["name"], styles["company"]),
        Spacer(1, 3*mm),
        Paragraph(addr_html, styles["company_addr"]),
    ]
    
    tbl = Table([[logo, company_block]], colWidths=[45*mm, 135*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return tbl


def _build_info_block(quotation: Dict[str, Any], styles) -> Table:
    """Two-column info block (Customer/Shipper/... | No./Date/...)."""
    left_rows = [
        ("Customer", quotation.get("customer_name", "")),
        ("Shpr/Cnee", quotation.get("shipper_cnee", "")),
        ("Carrier", quotation.get("carrier", "")),
        ("POL", quotation.get("pol", "")),
        ("POD", quotation.get("pod", "")),
        ("Attention", quotation.get("attention", "")),
        ("Tel.", quotation.get("tel", "")),
        ("Incoterm", quotation.get("incoterm", "")),
    ]
    right_rows = [
        ("No.", quotation.get("quotation_no", "")),
        ("Date", _format_date(quotation.get("quotation_date"))),
        ("Validity", _format_date(quotation.get("validity_date"))),
        ("Payment Term", quotation.get("payment_term", "30 Days")),
        ("Service Type", quotation.get("service_type", "")),
        ("Commodity", quotation.get("commodity", "")),
        ("Weight", quotation.get("weight", "")),
        ("Quantity", quotation.get("quantity_desc", "")),
    ]
    
    data = []
    for (l_label, l_val), (r_label, r_val) in zip(left_rows, right_rows):
        data.append([
            Paragraph(f"<b>{l_label}</b>", styles["label"]),
            Paragraph(f": {l_val}", styles["value"]),
            Paragraph(f"<b>{r_label}</b>", styles["label"]),
            Paragraph(f": {r_val}", styles["value"]),
        ])
    
    tbl = Table(data, colWidths=[24*mm, 70*mm, 26*mm, 60*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ("LINEABOVE", (0,0), (-1,0), 1, colors.black),
        ("LINEBELOW", (0,-1), (-1,-1), 1, colors.black),
    ]))
    return tbl


def _build_items_table(items: List[Dict[str, Any]], styles) -> Table:
    """Items table with auto-pagination support (header repeats on each page)."""
    header = [
        Paragraph('<b><font color="white">DESCIPTION</font></b>', styles["body"]),
        "", "", "", "",
    ]
    sub_header = [
        Paragraph('<b><font color="#1F4E9E">ITEM</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">CURR</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">PRICE</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">Unit</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">REMARK</font></b>', styles["body"]),
    ]
    
    data = [header, sub_header]
    for item in items:
        price = item.get("price", 0)
        price_str = f"{price:,.0f}" if price == int(price) else f"{price:,.2f}"
        data.append([
            Paragraph(item.get("description", ""), styles["body"]),
            Paragraph(item.get("currency", "USD"), styles["body"]),
            Paragraph(f"<b>{price_str}</b>", styles["body"]),
            Paragraph(item.get("unit", "") or "", styles["body"]),
            Paragraph(item.get("remark", "") or "", styles["body"]),
        ])
    
    tbl = Table(
        data,
        colWidths=[80*mm, 18*mm, 22*mm, 20*mm, 40*mm],
        repeatRows=2,  # Repeat both header rows on each page
    )
    tbl.setStyle(TableStyle([
        # Top "DESCIPTION" header row - blue background, spans full width
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), BRAND_BLUE),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        # Sub header row - grey background, all centered
        ("BACKGROUND", (0,1), (-1,1), HEADER_GREY),
        ("ALIGN", (0,1), (-1,1), "CENTER"),
        # Body
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,2), (0,-1), "LEFT"),     # Description left-aligned
        ("ALIGN", (1,2), (1,-1), "CENTER"),   # CURR centered
        ("ALIGN", (2,2), (2,-1), "CENTER"),   # PRICE centered
        ("ALIGN", (3,2), (3,-1), "CENTER"),   # Unit centered
        ("ALIGN", (4,2), (4,-1), "LEFT"),     # Remark left
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("INNERGRID", (0,0), (-1,1), 0.5, colors.black),
    ]))
    return tbl


def _build_terms(terms_text: str, styles) -> List:
    """Terms & Conditions block."""
    flowables = [
        Spacer(1, 4*mm),
        Paragraph(
            '<para><u><b>Terms &amp; Conditions:</b></u></para>',
            styles["tc_heading"],
        ),
    ]
    if not terms_text:
        return flowables
    for line in terms_text.strip().split("\n"):
        line = line.strip().lstrip("- ").strip()
        if not line:
            continue
        flowables.append(Paragraph(
            f'<para>- &nbsp; {line}</para>',
            styles["tc_item"],
        ))
    return flowables


def _build_signature(styles) -> Table:
    """Signature block: closing message + signature lines."""
    closing = Paragraph(
        "We do hope the above given rates will meet your requirements. "
        "Should any further information you may require, "
        "Please do not hesitate to contact us at your convenience. "
        "Looking forward to serving you soonest.",
        styles["body"],
    )
    
    sig_block = [
        Paragraph("Yours sincerely", styles["body"]),
        Spacer(1, 18*mm),
        Paragraph("_________________________________", styles["body"]),
        Paragraph(f"<b>{COMPANY['signer_name']}</b>", styles["body"]),
        Paragraph(COMPANY["signer_title"], styles["body"]),
        Paragraph(COMPANY["name"].title(), styles["body"]),
    ]
    customer_block = [
        Spacer(1, 18*mm + 12),
        Paragraph("_________________________________", styles["body"]),
        Paragraph("Authorized Signature", styles["body"]),
    ]
    
    tbl = Table([[sig_block, customer_block]], colWidths=[90*mm, 90*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    return tbl


def _page_decoration(canvas, doc):
    """Draw page footer 'Page X' on every page."""
    canvas.saveState()
    canvas.setFont(THAI_FONT, 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(
        A4[0] / 2, 10 * mm, f"Page {doc.page}"
    )
    canvas.restoreState()


def generate_quotation_pdf(
    quotation: Dict[str, Any],
    items: List[Dict[str, Any]],
    output_path: str | None = None,
) -> str:
    """Generate the A4 quotation PDF.
    
    Args:
        quotation: dict with quotation header fields (quotation_no, customer_name,
                   carrier, pol, pod, etc.)
        items: list of dicts with keys: description, currency, price, unit, remark
        output_path: optional output path. Defaults to OUTPUT_DIR/<quotation_no>.pdf
    
    Returns:
        The output file path as a string.
    """
    if output_path is None:
        qno = quotation.get("quotation_no", "quotation")
        output_path = str(Path(OUTPUT_DIR) / f"{qno}.pdf")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm,
        title=f"Quotation {quotation.get('quotation_no','')}",
        author=COMPANY["name"],
    )
    
    styles = _styles()
    story = []
    
    # 1. Header (logo + company)
    story.append(_build_header(styles))
    story.append(Spacer(1, 4*mm))
    
    # 2. Title "Quotation"
    story.append(Paragraph("<b>Quotation</b>", styles["title"]))
    
    # 3. Customer/Quotation info two-column block
    story.append(_build_info_block(quotation, styles))
    story.append(Spacer(1, 3*mm))
    
    # 4. Subject line
    subject = quotation.get("subject") or "Sea Import Shipment"
    story.append(Table(
        [[Paragraph("<b>Subject</b>", styles["label"]),
          Paragraph(f": {subject}", styles["value"])]],
        colWidths=[24*mm, 156*mm],
    ))
    story.append(Spacer(1, 3*mm))
    
    # 5. Intro paragraph
    story.append(Paragraph(
        "&nbsp;&nbsp;&nbsp;&nbsp;Thank you for opportunity extended to us in "
        "putting a proposal to your requirements. We would be very pleased to "
        "take this opportunity to offer your esteemed company our competitive "
        "rates as below for your kind consideration and perusal.",
        styles["body"],
    ))
    story.append(Spacer(1, 4*mm))
    
    # 6. Items table (auto-paginates)
    story.append(_build_items_table(items, styles))
    story.append(Spacer(1, 3*mm))
    
    # 7. Terms & Conditions
    terms = quotation.get("terms_conditions", "")
    for fl in _build_terms(terms, styles):
        story.append(fl)
    
    # 8. Signature block
    story.append(Spacer(1, 6*mm))
    story.append(_build_signature(styles))
    
    doc.build(
        story,
        onFirstPage=_page_decoration,
        onLaterPages=_page_decoration,
    )
    return output_path
