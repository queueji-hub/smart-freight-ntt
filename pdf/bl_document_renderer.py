"""Pure company-issued Ocean Bill of Lading renderer.

Layout matches the supplied NATTAYAARAT Ocean B/L sample exactly:
  - Emerald Green borders & labels (#15803D / #16A34A)
  - Company Header with logo, Thai & English name, tax ID, and registered address
  - B/L Number box at top-right
  - Shipper, Consignee, Notify Party boxes on the left
  - "For Delivery of Goods Please Apply to" delivery agent box on the right
  - Routing grid: Pre-Carriage by, Place of Receipt, Ocean Vessel/Voyage No., Port of Loading,
    Port of Discharge, Place of Delivery, Final Destination
  - Cargo 5-column table: Marks & Numbers/Container & Seal, No. of Packages, Description, Gross Weight, CBM
  - Freight & Disbursements breakdown table
  - Standard Carrier legal clauses
  - Issuance details: Freight payable at, Place and date of issue, Number of original B/Ls, Signature block
  - Watermark: COPY / ORIGINAL across page center

Consumes a validated payload and performs zero database writes.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import register_thai_fonts

FONT, FONT_BOLD = register_thai_fonts()

# Color Palette matching the sample document
BORDER_GREEN = colors.HexColor("#15803D")
LABEL_GREEN = colors.HexColor("#15803D")
TEXT_DARK = colors.HexColor("#0F172A")
TITLE_NAVY = colors.HexColor("#1E3A8A")
BG_LIGHT = colors.HexColor("#F8FAFC")
BG_HEADER = colors.HexColor("#F0FDF4")
WATERMARK_COLOR = colors.Color(0.72, 0.72, 0.72, alpha=0.18)

TOTAL_W = 194 * mm


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "nan", "nat"} else text


def _date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%B %d, %Y").upper()
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%B %d, %Y").upper()
    except Exception:
        return _s(value)


def _num(value: Any, precision: int = 2, unit: str = "") -> str:
    try:
        n = float(value or 0)
        if n == 0:
            return ""
        formatted = f"{n:,.{precision}f}"
        return f"{formatted} {unit}".strip() if unit else formatted
    except (TypeError, ValueError):
        return ""


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "company_th": ParagraphStyle("bl_company_th", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=10.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "company_en": ParagraphStyle("bl_company_en", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=10.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "company_addr": ParagraphStyle("bl_company_addr", parent=base["Normal"], fontName=FONT, fontSize=5.6, leading=7.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "doc_title": ParagraphStyle("bl_doc_title", parent=base["Normal"], fontName=FONT_BOLD, fontSize=12.5, leading=14.5, alignment=TA_CENTER, textColor=TITLE_NAVY),
        "bl_no_top": ParagraphStyle("bl_no_top", parent=base["Normal"], fontName=FONT, fontSize=7.5, leading=9, textColor=TEXT_DARK),
        "label": ParagraphStyle("bl_label", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.2, leading=7.5, textColor=LABEL_GREEN),
        "value": ParagraphStyle("bl_value", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8.5, textColor=TEXT_DARK),
        "value_bold": ParagraphStyle("bl_value_bold", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.0, leading=8.5, textColor=TEXT_DARK),
        "cargo_head": ParagraphStyle("bl_cargo_head", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.2, leading=7.5, alignment=TA_CENTER, textColor=LABEL_GREEN),
        "cargo_cell": ParagraphStyle("bl_cargo_cell", parent=base["Normal"], fontName=FONT, fontSize=6.4, leading=8.0, textColor=TEXT_DARK),
        "cargo_center": ParagraphStyle("bl_cargo_center", parent=base["Normal"], fontName=FONT, fontSize=6.4, leading=8.0, alignment=TA_CENTER, textColor=TEXT_DARK),
        "cargo_bold_center": ParagraphStyle("bl_cargo_bold_center", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.6, leading=8.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "legal": ParagraphStyle("bl_legal", parent=base["Normal"], fontName=FONT, fontSize=4.8, leading=5.8, alignment=TA_JUSTIFY, textColor=LABEL_GREEN),
        "sign": ParagraphStyle("bl_sign", parent=base["Normal"], fontName=FONT, fontSize=6.2, leading=7.5, alignment=TA_LEFT, textColor=LABEL_GREEN),
        "terms_watermark": ParagraphStyle("bl_terms_wm", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.0, leading=10, alignment=TA_CENTER, textColor=TEXT_DARK),
    }


def _draw_watermark(canvas, doc, watermark_text: str = "COPY"):
    canvas.saveState()
    canvas.setFont(FONT_BOLD, 68)
    canvas.setFillColor(WATERMARK_COLOR)
    canvas.translate(A4[0] / 2, A4[1] * 0.42)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, watermark_text)
    canvas.restoreState()


def generate_company_bl_pdf(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    if not isinstance(payload, dict) or "bl" not in payload:
        raise ValueError("B/L PDF requires a validated payload dict with a 'bl' record.")

    bl = dict(payload.get("bl") or {})
    job = dict(payload.get("job") or {})
    containers = list(payload.get("containers") or [])
    styles = _styles()

    bl_no = _s(bl.get("bl_no"), "NATTA-BKKSGN2608001")
    approval_status = _s(bl.get("approval_status") or bl.get("status"), "Draft")

    shipper = _s(bl.get("shipper"))
    consignee = _s(bl.get("consignee"))
    notify = _s(bl.get("notify_party"), "SAME AS CONSIGNEE")
    delivery_agent = _s(bl.get("delivery_agent"))
    pre_carriage = _s(bl.get("pre_carriage_by"))
    place_receipt = _s(bl.get("place_of_receipt") or job.get("place_of_receipt"))

    # Ocean Vessel & Voyage
    vessel = _s(bl.get("vessel") or job.get("vessel") or job.get("mother_vessel"))
    voyage = _s(bl.get("voyage") or job.get("voyage") or job.get("mother_voyage"))
    vessel_voyage = f"{vessel} {voyage}".strip() or "—"

    pol = _s(bl.get("port_of_loading") or job.get("pol"))
    pod = _s(bl.get("port_of_discharge") or job.get("pod"))
    place_delivery = _s(bl.get("place_of_delivery") or job.get("place_of_delivery") or pod)
    final_destination = _s(bl.get("final_destination"))

    freight = _s(bl.get("freight_term") or job.get("freight_term"), "PREPAID").upper()
    freight_term_display = f"FREIGHT {freight}"
    freight_payable = _s(bl.get("freight_payable_at") or ("Bangkok, Thailand" if freight == "PREPAID" else pod))
    issue_place = _s(bl.get("place_of_issue"), "BANGKOK, THAILAND")
    originals = _s(bl.get("number_of_originals"), "3 (THREE)")
    if originals == "3":
        originals = "3 (THREE)"
    bl_date_str = _date(bl.get("bl_date") or date.today())
    place_date_issue = f"{issue_place}, {bl_date_str}" if bl_date_str else issue_place

    marks = _s(bl.get("marks_numbers"))
    goods = _s(bl.get("description_of_goods") or job.get("commodity"))
    hs = _s(bl.get("hs_code") or job.get("hs_code"))
    packages_val = _s(bl.get("package_qty"))
    pkg_type = _s(bl.get("package_type"), "PALLETS")
    gross_val = _num(bl.get("gross_weight"), precision=2, unit="KGS")
    cbm_val = _num(bl.get("measurement_cbm"), precision=3, unit="CBM")

    # Output path
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"BL_{bl_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=7 * mm,
        bottomMargin=7 * mm,
        title=f"Bill of Lading {bl_no}",
        author=COMPANY.get("name", "NATTAYAARAT CO., LTD."),
    )

    story = []

    # =========================================================================
    # 1. TOP HEADER & PARTIES SECTION
    # =========================================================================
    logo_path = COMPANY.get("logo_path")
    logo_img = None
    if logo_path and Path(str(logo_path)).exists():
        try:
            ir = ImageReader(str(logo_path))
            iw, ih = ir.getSize()
            scale = min(24 * mm / iw, 14 * mm / ih)
            logo_img = Image(str(logo_path), width=iw * scale, height=ih * scale)
        except Exception:
            logo_img = None

    comp_name_th = _s(COMPANY.get("name_th", "บริษัท ณัฐยาราชย์ จำกัด"))
    comp_name_en = _s(COMPANY.get("name_en", "NATTAYAARAT CO., LTD."))
    comp_addr = (
        f"{_s(COMPANY.get('address_line1', '59/91 THE BALANZ ZIGMA VILLAGE, MOO4, SOI BANGKRATHUEK 3,'))}<br/>"
        f"{_s(COMPANY.get('address_line2', 'BANGKRATHUEK SUBDISTRICT, SAMPHRAN DISTRICT,'))} "
        f"{_s(COMPANY.get('address_line3', 'NAKHON PATHOM PROVINCE 73210'))}<br/>"
        f"TAX ID: {_s(COMPANY.get('tax_id', '073-558-800-4823'))}"
    )

    header_text_cells = [
        Paragraph(f"<b>{comp_name_th}</b>", styles["company_th"]),
        Paragraph(f"<b>{comp_name_en}</b>", styles["company_en"]),
        Paragraph(comp_addr, styles["company_addr"]),
        Spacer(1, 1 * mm),
        Paragraph("<b>BILL OF LADING</b>", styles["doc_title"]),
    ]

    header_logo_table = Table(
        [[logo_img or "", header_text_cells]],
        colWidths=[24 * mm, 68 * mm]
    )
    header_logo_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    header_right_box = [
        Paragraph(f"<b><font color='#15803D'>B/L No.</font></b> <b>{bl_no}</b>", styles["bl_no_top"]),
        Spacer(1, 1.5 * mm),
        header_logo_table,
    ]

    shipper_content = [
        Paragraph("<b>Shipper</b>", styles["label"]),
        Paragraph(shipper.replace("\n", "<br/>") if shipper else "—", styles["value"]),
    ]

    top_row_table = Table(
        [[shipper_content, header_right_box]],
        colWidths=[100 * mm, 94 * mm]
    )
    top_row_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(top_row_table)

    # Consignee & Notify (Left) and Delivery Agent (Right)
    consignee_content = [
        Paragraph("<b>Consignee</b>", styles["label"]),
        Paragraph(consignee.replace("\n", "<br/>") if consignee else "—", styles["value"]),
    ]

    notify_content = [
        Paragraph("<b>Notify Party</b>", styles["label"]),
        Paragraph(notify.replace("\n", "<br/>") if notify else "SAME AS CONSIGNEE", styles["value"]),
    ]

    left_parties_table = Table(
        [[consignee_content], [notify_content]],
        colWidths=[100 * mm],
        rowHeights=[24 * mm, 16 * mm]
    )
    left_parties_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
    ]))

    agent_content = [
        Paragraph("<b>For Delivery of Goods Please Apply to</b>", styles["label"]),
        Spacer(1, 1 * mm),
        Paragraph(delivery_agent.replace("\n", "<br/>") if delivery_agent else "—", styles["value"]),
    ]

    parties_middle_table = Table(
        [[left_parties_table, agent_content]],
        colWidths=[100 * mm, 94 * mm]
    )
    parties_middle_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 3.5),
        ("RIGHTPADDING", (1, 0), (1, 0), 3.5),
        ("TOPPADDING", (1, 0), (1, 0), 2.5),
        ("BOTTOMPADDING", (1, 0), (1, 0), 2.5),
    ]))
    story.append(parties_middle_table)

    # =========================================================================
    # 2. ROUTING MATRIX SECTION
    # =========================================================================
    routing_data = [
        [
            [Paragraph("<b>Pre-Carriage by</b>", styles["label"]), Paragraph(_s(pre_carriage), styles["value"])],
            [Paragraph("<b>Place of Receipt</b>", styles["label"]), Paragraph(_s(place_receipt), styles["value_bold"])],
            "",
        ],
        [
            [Paragraph("<b>Ocean Vessel / Voyage No.</b>", styles["label"]), Paragraph(vessel_voyage, styles["value_bold"])],
            [Paragraph("<b>Port of Loading</b>", styles["label"]), Paragraph(_s(pol), styles["value_bold"])],
            "",
        ],
        [
            [Paragraph("<b>Port of Discharge</b>", styles["label"]), Paragraph(_s(pod), styles["value_bold"])],
            [Paragraph("<b>Place of Delivery</b>", styles["label"]), Paragraph(_s(place_delivery), styles["value_bold"])],
            [Paragraph("<b>Final Destination (For The Merchant's Reference Only)</b>", styles["label"]), Paragraph(_s(final_destination), styles["value"])],
        ],
    ]

    routing_table = Table(
        routing_data,
        colWidths=[58 * mm, 68 * mm, 68 * mm],
        rowHeights=[10 * mm, 10 * mm, 11 * mm]
    )
    routing_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("SPAN", (1, 0), (2, 0)),
        ("SPAN", (1, 1), (2, 1)),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(routing_table)

    # =========================================================================
    # 3. CARGO & CONTAINER MANIFEST TABLE
    # =========================================================================
    cargo_headers = [
        Paragraph("<b>Marks and Numbers<br/>Container & Seal Numbers</b>", styles["cargo_head"]),
        Paragraph("<b>No. of Packages</b>", styles["cargo_head"]),
        Paragraph("<b>Description of Packages and Goods<br/>Packages Forwarded by Shipper</b>", styles["cargo_head"]),
        Paragraph("<b>Gross Weight Kgs</b>", styles["cargo_head"]),
        Paragraph("<b>Measurement CBM</b>", styles["cargo_head"]),
    ]

    # Assemble container lines
    cnt_lines = []
    if containers:
        cnt_lines.append("SHIPPED IN CONTAINER")
        for c in containers:
            cno = _s(c.get("container_no"))
            ctype = _s(c.get("container_size") or c.get("container_type"))
            seal = _s(c.get("seal_no") or c.get("seal"))
            cnt_desc = f"CONTAINER NO. {cno}" + (f"/{ctype}" if ctype else "")
            cnt_lines.append(cnt_desc)
            if seal:
                cnt_lines.append(f"SEAL NUM: {seal}")
    else:
        cnt_summary = _s(bl.get("container_summary"))
        if cnt_summary:
            cnt_lines.append("SHIPPED IN CONTAINER")
            cnt_lines.append(cnt_summary)

    marks_block = []
    if marks and marks != "N/M":
        marks_block.append(marks.replace("\n", "<br/>"))
    if cnt_lines:
        if marks_block:
            marks_block.append("<br/>")
        marks_block.append("<br/>".join(cnt_lines))

    marks_html = "<br/>".join(marks_block) if marks_block else "N/M"

    pkg_text = f"{packages_val} {pkg_type}".strip() if packages_val else ""

    desc_parts = []
    desc_parts.append("SAID TO CONTAINER(CY-CY)<br/>SHIPPER'S LOAD & COUNT & SEAL")
    if goods:
        desc_parts.append(goods.replace("\n", "<br/>"))
    if hs:
        desc_parts.append(f"HS CODE: {hs}")
    if pkg_text:
        desc_parts.append(f"<br/>{pkg_text.upper()} ONLY")

    desc_html = "<br/>".join(desc_parts)

    cargo_body_row = [
        Paragraph(marks_html, styles["cargo_cell"]),
        Paragraph(f"<b>{pkg_text}</b>", styles["cargo_center"]),
        Paragraph(desc_html, styles["cargo_cell"]),
        Paragraph(f"<b>{gross_val}</b>", styles["cargo_center"]),
        Paragraph(f"<b>{cbm_val}</b>", styles["cargo_center"]),
    ]

    # Freight status footer row inside cargo block
    freight_term_cell = Paragraph(f"<b>{freight_term_display}</b>", styles["terms_watermark"])

    cargo_table = Table(
        [
            cargo_headers,
            cargo_body_row,
            ["", "", freight_term_cell, "", ""],
        ],
        colWidths=[48 * mm, 26 * mm, 72 * mm, 24 * mm, 24 * mm],
        rowHeights=[8 * mm, 62 * mm, 7 * mm]
    )
    cargo_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("BACKGROUND", (0, 0), (-1, 0), BG_HEADER),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (0, 1), (-1, 1), "TOP"),
        ("VALIGN", (0, 2), (-1, 2), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.0),
        ("TOPPADDING", (0, 0), (-1, -1), 2.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
    ]))
    story.append(cargo_table)

    # =========================================================================
    # 4. FREIGHT & DISBURSEMENTS BREAKDOWN & CARRIER CLAUSES
    # =========================================================================
    freight_table_data = [
        [
            Paragraph("<b>Freight and Disbursements</b>", styles["cargo_head"]),
            Paragraph("<b>Rate at<br/>KGS/Tons</b>", styles["cargo_head"]),
            Paragraph("<b>Prepaid</b>", styles["cargo_head"]),
            Paragraph("<b>Collect</b>", styles["cargo_head"]),
        ],
        [
            Paragraph("", styles["cargo_cell"]),
            Paragraph("", styles["cargo_cell"]),
            Paragraph(f"<b>{freight}</b>" if freight == "PREPAID" else "", styles["cargo_bold_center"]),
            Paragraph(f"<b>{freight}</b>" if freight == "COLLECT" else "", styles["cargo_bold_center"]),
        ],
        [
            Paragraph("<b>Total</b>", styles["cargo_head"]),
            Paragraph("", styles["cargo_cell"]),
            Paragraph("", styles["cargo_cell"]),
            Paragraph("", styles["cargo_cell"]),
        ],
    ]

    freight_box = Table(
        freight_table_data,
        colWidths=[26 * mm, 18 * mm, 17 * mm, 17 * mm],
        rowHeights=[7.5 * mm, 17.5 * mm, 6.5 * mm]
    )
    freight_box.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("BACKGROUND", (0, 0), (-1, 0), BG_HEADER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
        ("TOPPADDING", (0, 0), (-1, -1), 1.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.0),
    ]))

    carrier_legal_clauses = (
        "RECEIVED by the Carrier the Goods as specified above in apparent good order and condition unless otherwise stated, to be "
        "transported to such place as agreed, authorized or permitted herein and subject to all the terms and conditions appearing "
        "on the front and back of this Bill of Lading to which the Merchant agrees by accepting this Bill of Lading, any local privileges "
        "and customs notwithstanding.<br/>"
        "The particulars given below as stated by the shipper and the weight, measure, quantity, condition, contents and value of the "
        "goods are unknown to the Carrier.<br/>"
        "IN WITNESS whereof (insert original) of Bill of Lading has been signed if not otherwise stated above, the same being "
        "accomplished, the other(s), if any, to be void. If required by the Carrier one (1) original Bill of Lading must be surrendered "
        "duly endorsed in exchange for the Goods or delivery order."
    )

    terms_box = Table(
        [[Paragraph(carrier_legal_clauses, styles["legal"])]],
        colWidths=[116 * mm],
        rowHeights=[31.5 * mm]
    )
    terms_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
    ]))

    freight_and_terms = Table(
        [[freight_box, terms_box]],
        colWidths=[78 * mm, 116 * mm]
    )
    freight_and_terms.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(freight_and_terms)

    # =========================================================================
    # 5. ISSUANCE & SIGNATURE FOOTER
    # =========================================================================
    issuance_col1 = [
        Paragraph("<b>Freight payable at</b>", styles["label"]),
        Paragraph(_s(freight_payable), styles["value_bold"]),
        Spacer(1, 2 * mm),
        Paragraph("<b>Number of original B/Ls</b>", styles["label"]),
        Paragraph(_s(originals), styles["value_bold"]),
    ]

    issuance_col2 = [
        Paragraph("<b>Place and date of issue</b>", styles["label"]),
        Paragraph(place_date_issue, styles["value_bold"]),
    ]

    issuance_col3 = [
        Paragraph("<b>Signed on behalf of the Carrier :</b>", styles["sign"]),
        Spacer(1, 14 * mm),
        Paragraph("By ____________________________________", styles["sign"]),
    ]

    footer_table = Table(
        [[issuance_col1, issuance_col2, issuance_col3]],
        colWidths=[65 * mm, 65 * mm, 64 * mm],
        rowHeights=[26 * mm]
    )
    footer_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(footer_table)

    watermark_label = "ORIGINAL" if approval_status.lower() in {"approved", "issued", "released"} else "COPY"

    doc.build(
        story,
        onFirstPage=lambda canvas, d: _draw_watermark(canvas, d, watermark_label),
        onLaterPages=lambda canvas, d: _draw_watermark(canvas, d, watermark_label),
    )
    return output_path
