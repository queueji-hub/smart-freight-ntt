"""A4 Quotation PDF generator (matches Nattayaraat layout)."""
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Any
import re

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
            d = datetime.strptime(d[:10], "%Y-%m-%d").date()
        except ValueError:
            return d
    return d.strftime("%d-%m-%y")


def _clean_text(val: Any) -> str:
    """Strips internal codes (e.g. 'BP001 — ', 'C0001 — ', 'SP001 — ') for clean customer-facing PDF presentation."""
    if val is None:
        return ""
    text = str(val).strip()
    if not text or text.lower() in {"none", "nan", "nat"}:
        return ""
    if " — " in text:
        parts = text.split(" — ", 1)
        if len(parts[0]) <= 8 and (parts[0].isalnum() or parts[0].startswith(("BP", "C", "SP", "P", "CHG", "USR"))):
            return parts[1].strip()
    elif " - " in text:
        parts = text.split(" - ", 1)
        if len(parts[0]) <= 8 and (parts[0].isalnum() or parts[0].startswith(("BP", "C", "SP", "P", "CHG", "USR"))):
            return parts[1].strip()
    return text


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
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(logo_path)
        iw, ih = img_reader.getSize()
        max_w, max_h = 45*mm, 28*mm
        scale = min(max_w / iw, max_h / ih)
        logo = Image(logo_path, width=iw*scale, height=ih*scale)
    else:
        logo = Paragraph("<b>[LOGO]</b>", styles["body"])
    
    addr_html = (
        f'<font size="8" color="#1F4E9E">'
        f'<b>{COMPANY.get("name_th", "บริษัท ณัฏฐยาราชย์ จำกัด")}</b><br/>'
        f'{COMPANY["address_line1"]}<br/>'
        f'{COMPANY["address_line2"]} {COMPANY["address_line3"]}<br/>'
        f'<b>Tax ID: {COMPANY["tax_id"]}</b> | Tel: {COMPANY["tel"]}<br/>'
        f'Email: {COMPANY["email"]} | Web: {COMPANY["website"]}'
        f'</font>'
    )
    company_block = [
        Paragraph(COMPANY["name_en"], styles["company"]),
        Spacer(1, 1*mm),
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
    def _safe_str(val):
        return str(val) if val is not None and str(val).strip() not in {"None", "nan", "NaN"} else ""
        
    def _safe_num(val, suffix=""):
        if not val or val in {"None", "nan", "NaN"}:
            return ""
        try:
            num = float(val)
            if num == 0:
                return ""
            num_str = f"{num:,.3f}".rstrip('0').rstrip('.')
            return f"{num_str} {suffix}".strip()
        except (ValueError, TypeError):
            return f"{val} {suffix}".strip()

    left_rows = [
        ("Customer", _clean_text(quotation.get("customer_name"))),
        ("Address", _safe_str(quotation.get("customer_address"))),
        ("Attention", _safe_str(quotation.get("attention"))),
        ("Shipper", _clean_text(quotation.get("shipper"))),
        ("Consignee", _clean_text(quotation.get("consignee"))),
        ("POL", _safe_str(quotation.get("pol"))),
        ("POD", _safe_str(quotation.get("pod"))),
        ("Incoterm", _safe_str(quotation.get("incoterm"))),
    ]
    
    qty_str = ""
    if _safe_num(quotation.get("quantity")):
        qty_str = f"{_safe_num(quotation.get('quantity'))} {_safe_str(quotation.get('package_type'))}".strip()
        
    vol_str = []
    if _safe_num(quotation.get("weight_kg")):
        vol_str.append(_safe_num(quotation.get("weight_kg"), "KGs"))
    if _safe_num(quotation.get("volume_cbm")):
        vol_str.append(_safe_num(quotation.get("volume_cbm"), "CBM"))
        
    cont_str = ""
    if _safe_num(quotation.get("container_quantity")):
        cont_str = f"{_safe_num(quotation.get('container_quantity'))}x {_safe_str(quotation.get('container_type'))}".strip()

    salesperson_name = _clean_text(quotation.get("salesperson") or quotation.get("sales_person"))
    right_rows = [
        ("No.", _safe_str(quotation.get("quotation_no"))),
        ("Date", _format_date(quotation.get("quotation_date"))),
        ("Validity", _format_date(quotation.get("validity_date"))),
        ("Salesperson", salesperson_name or "—"),
        ("Payment Term", _safe_str(quotation.get("payment_term"))),
        ("Commodity", _safe_str(quotation.get("commodity"))),
        ("Service Type", _safe_str(quotation.get("service_type"))),
        ("Volume/Qty", " / ".join([s for s in [qty_str, " ".join(vol_str), cont_str] if s]) or "—"),
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
        Paragraph('<b><font color="white">DESCRIPTION</font></b>', styles["body"]),
        "", "", "", "", "", ""
    ]
    sub_header = [
        Paragraph('<b><font color="#1F4E9E">ITEM</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">QTY</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">UNIT</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">CURR</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">RATE</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">AMOUNT</font></b>', styles["body"]),
        Paragraph('<b><font color="#1F4E9E">REMARK</font></b>', styles["body"]),
    ]
    
    data = [header, sub_header]
    currency_totals = {}
    
    for item in items:
        amount = float(item.get("amount") or item.get("price") or 0)
        rate = float(item.get("unit_rate") or amount)
        qty = float(item.get("quantity") if item.get("quantity") is not None else 1.0)
        curr = str(item.get("currency") or "USD").upper()
        
        desc = _clean_text(item.get("description", "")) or ""
        unit = _clean_text(item.get("unit") or item.get("basis") or "")
        
        currency_totals[curr] = currency_totals.get(curr, 0) + amount
        
        qty_display = f"{qty:,.3f}".rstrip('0').rstrip('.') if qty != int(qty) else str(int(qty))
        
        data.append([
            Paragraph(desc, styles["body"]),
            Paragraph(qty_display, styles["body"]),
            Paragraph(unit, styles["body"]),
            Paragraph(curr, styles["body"]),
            Paragraph(f"{rate:,.2f}", styles["body"]),
            Paragraph(f"<b>{amount:,.2f}</b>", styles["body"]),
            Paragraph(str(item.get("remark") or ""), styles["body"]),
        ])
    
    # Add Total Rows by Currency
    if currency_totals:
        for curr, tot in currency_totals.items():
            if tot > 0:
                data.append([
                    "", "", "", "",
                    Paragraph(f"<b>Total {curr}:</b>", styles["body"]),
                    Paragraph(f"<b>{tot:,.2f}</b>", styles["body"]),
                    ""
                ])
    
    tbl = Table(
        data,
        colWidths=[55*mm, 15*mm, 15*mm, 15*mm, 20*mm, 25*mm, 35*mm],
        repeatRows=2,
    )
    tbl.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), BRAND_BLUE),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("BACKGROUND", (0,1), (-1,1), HEADER_GREY),
        ("ALIGN", (0,1), (-1,1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,2), (0,-1), "LEFT"),
        ("ALIGN", (1,2), (1,-1), "CENTER"),
        ("ALIGN", (2,2), (2,-1), "CENTER"),
        ("ALIGN", (3,2), (3,-1), "CENTER"),
        ("ALIGN", (4,2), (4,-1), "RIGHT"),
        ("ALIGN", (5,2), (5,-1), "RIGHT"),
        ("ALIGN", (6,2), (6,-1), "LEFT"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("INNERGRID", (0,0), (-1,len(items)+1), 0.5, colors.black),
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
        line = re.sub(r"^(\d+[\.\)]\s*|-\s*|\*\s*)", "", line.strip()).strip()
        if not line:
            continue
        flowables.append(Paragraph(
            f'<para>- &nbsp; {line}</para>',
            styles["tc_item"],
        ))
    return flowables


def _build_signature(styles, quotation: Dict[str, Any] = None) -> Table:
    """Signature block: closing message + signature lines."""
    sp_name = _clean_text((quotation or {}).get("salesperson") or (quotation or {}).get("sales_person")) or COMPANY['signer_name']
    
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
        Paragraph(f"<b>{sp_name}</b>", styles["body"]),
        Paragraph("Sales Executive" if sp_name != COMPANY['signer_name'] else COMPANY["signer_title"], styles["body"]),
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
    quotation: Any,
    items: List[Dict[str, Any]] | None = None,
    output_path: str | None = None,
) -> str:
    """Generate the A4 quotation PDF without internal codes."""
    if isinstance(quotation, str):
        from managers.quotation_manager import get_quotation_by_no
        q_doc = get_quotation_by_no(quotation)
        if not q_doc:
            raise ValueError(f"Quotation '{quotation}' not found.")
        quotation = q_doc

    if items is None:
        items = quotation.get("items", [])

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
    subject = quotation.get("subject") or "Freight Quotation"
    story.append(Table(
        [[Paragraph("<b>Subject</b>", styles["label"]),
          Paragraph(f": {_clean_text(subject)}", styles["value"])]],
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
    story.append(_build_signature(styles, quotation))
    
    doc.build(
        story,
        onFirstPage=_page_decoration,
        onLaterPages=_page_decoration,
    )
    return output_path
