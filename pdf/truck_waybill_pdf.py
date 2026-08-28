"""Pure ReportLab Truck Waybill PDF generator.

Layout matches the official Truck Waybill reference specification exactly:
- Header: Title 'TRUCK WAY BILL' with sub-caption and 'Job Ref No. #'
- Upper 2-column block:
  - Shipper Name & Address vs TRUCK WAY BILL NUMBER
  - Consignee Name & Address vs Truck AWB Issued By (Logo, Company Profile, Tax ID)
  - Notify Party vs Delivery Agent
  - Booking Party vs Accounting Information
  - Origin vs Destination
- Particulars Banner: 'PARTICULARS FURNISHED BY SHIPPER - CARRIER/AGENT NOT RESPONSIBLE'
- 6-Column Cargo Table: No of Pieces, Gross Weight (kgs.), Vol. Wght (kgs.), Wght (kgs), Description, Dimension
- Total row
- Invoice Details & Customer Ref #
- Legal Disclaimer
- Bottom Left: Move Type, Freight Charges, Duty/Other, Origin/Destination Charges
- Bottom Right: Shipper Confirmation & Carrier Acceptance declaration with Signature & Company Stamp
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

BORDER_COLOR = colors.HexColor("#1E293B")
TEXT_DARK = colors.HexColor("#0F172A")
LABEL_COLOR = colors.HexColor("#334155")
BG_HEADER = colors.HexColor("#F1F5F9")
WATERMARK_COLOR = colors.Color(0.75, 0.75, 0.75, alpha=0.18)

TOTAL_W = 196 * mm


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "nan", "nat"} else text


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
        "title_main": ParagraphStyle("twb_title", parent=base["Normal"], fontName=FONT_BOLD, fontSize=14, leading=16, textColor=TEXT_DARK),
        "title_sub": ParagraphStyle("twb_sub", parent=base["Normal"], fontName=FONT, fontSize=6.5, leading=8, textColor=LABEL_COLOR),
        "job_ref": ParagraphStyle("twb_job_ref", parent=base["Normal"], fontName=FONT_BOLD, fontSize=10, leading=12, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "label": ParagraphStyle("twb_label", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.5, leading=8, textColor=LABEL_COLOR),
        "label_right": ParagraphStyle("twb_label_r", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.8, leading=8, alignment=TA_RIGHT, textColor=LABEL_COLOR),
        "value": ParagraphStyle("twb_value", parent=base["Normal"], fontName=FONT, fontSize=7.2, leading=9, textColor=TEXT_DARK),
        "value_bold": ParagraphStyle("twb_value_b", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8, leading=10, textColor=TEXT_DARK),
        "value_bold_right": ParagraphStyle("twb_value_br", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=10.5, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "comp_name": ParagraphStyle("twb_comp_name", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.0, leading=9.5, textColor=TEXT_DARK),
        "comp_addr": ParagraphStyle("twb_comp_addr", parent=base["Normal"], fontName=FONT, fontSize=5.5, leading=7.0, textColor=TEXT_DARK),
        "banner": ParagraphStyle("twb_banner", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.2, leading=7.5, alignment=TA_CENTER, textColor=LABEL_COLOR),
        "table_head": ParagraphStyle("twb_thead", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.5, leading=8, alignment=TA_CENTER, textColor=LABEL_COLOR),
        "table_cell": ParagraphStyle("twb_tcell", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8.5, textColor=TEXT_DARK),
        "table_cell_center": ParagraphStyle("twb_tcell_c", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "disclaimer": ParagraphStyle("twb_disc", parent=base["Normal"], fontName=FONT, fontSize=5.2, leading=6.5, alignment=TA_CENTER, textColor=LABEL_COLOR),
        "terms": ParagraphStyle("twb_terms", parent=base["Normal"], fontName=FONT, fontSize=5.2, leading=6.6, alignment=TA_JUSTIFY, textColor=TEXT_DARK),
        "summary_label": ParagraphStyle("twb_slabel", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.0, leading=9, textColor=LABEL_COLOR),
        "summary_val": ParagraphStyle("twb_sval", parent=base["Normal"], fontName=FONT, fontSize=7.0, leading=9, textColor=TEXT_DARK),
    }


def _draw_watermark(canvas, doc, watermark_text: str = "COPY"):
    canvas.saveState()
    canvas.setFont(FONT_BOLD, 68)
    canvas.setFillColor(WATERMARK_COLOR)
    canvas.translate(A4[0] / 2, A4[1] * 0.42)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, watermark_text)
    canvas.restoreState()


def generate_truck_waybill_pdf(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    bl = dict(payload.get("bl") or {})
    job = dict(payload.get("job") or {})
    booking = dict(payload.get("booking") or {})
    containers = list(payload.get("containers") or [])
    styles = _styles()

    twb_no = _s(bl.get("truck_waybill_no") or bl.get("bl_no"), "TWB-2608-0001")
    job_no = _s(bl.get("job_no") or job.get("job_no"), "—")
    approval_status = _s(bl.get("approval_status") or bl.get("status"), "Draft")

    shipper = _s(bl.get("shipper"))
    consignee = _s(bl.get("consignee"))
    notify = _s(bl.get("notify_party"), "SAME AS CONSIGNEE")
    delivery_agent = _s(bl.get("delivery_agent"))
    booking_party = _s(bl.get("booking_party") or job.get("customer_name") or shipper)
    accounting_info = _s(bl.get("accounting_info"), "FREIGHT PREPAID / ISSUED AS PER AGREEMENT")

    origin = _s(bl.get("origin") or bl.get("port_of_loading") or job.get("pol") or "BANGKOK, THAILAND")
    destination = _s(bl.get("destination") or bl.get("port_of_discharge") or job.get("pod") or "VIENTIANE, LAOS")

    package_qty = _s(bl.get("package_qty")) or "1"
    package_type = _s(bl.get("package_type"), "PKGS")
    gross_wt = _s(bl.get("gross_weight"))
    vol_wt = _s(bl.get("volumetric_weight"))
    actual_wt = _s(bl.get("gross_weight"))
    description = _s(bl.get("description_of_goods") or job.get("commodity") or "SAID TO CONTAIN GENERAL MERCHANDISE")
    dimension = _s(bl.get("dimension"), "AS PER PACKING LIST")

    invoice_details = _s(bl.get("invoice_details") or job.get("invoice_no") or "INV-COMMERCIAL")
    customer_ref = _s(bl.get("customer_ref_no") or job.get("customer_reference") or job_no)

    move_type = _s(bl.get("move_type") or bl.get("truck_type") or "Full Truck Load (FTL)")
    freight_charges = _s(bl.get("freight_charges")) or "AS AGREED"
    duty_charges = _s(bl.get("duty_other_charges")) or "—"
    origin_charges = _s(bl.get("origin_charges")) or "—"
    dest_charges = _s(bl.get("destination_charges")) or "—"

    # Output path
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"TWB_{twb_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=7 * mm,
        rightMargin=7 * mm,
        topMargin=7 * mm,
        bottomMargin=7 * mm,
        title=f"Truck Waybill {twb_no}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )

    story = []

    # =========================================================================
    # 1. TOP TITLE & JOB REF
    # =========================================================================
    title_cell = [
        Paragraph("<b>TRUCK WAY BILL</b>", styles["title_main"]),
        Spacer(1, 0.5 * mm),
        Paragraph("To be used for Single Consignment, Full Truck Load and Less Truck Load", styles["title_sub"]),
    ]
    job_ref_cell = [
        Paragraph(f"<b>Job Ref No. # {job_no}</b>", styles["job_ref"]),
    ]
    top_header_table = Table([[title_cell, job_ref_cell]], colWidths=[120 * mm, 76 * mm])
    top_header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story.append(top_header_table)

    # =========================================================================
    # 2. UPPER 2-COLUMN GRID (Parties, Company Logo, Routing)
    # =========================================================================
    logo_path = COMPANY.get("logo_path")
    logo_img = ""
    if logo_path and Path(str(logo_path)).exists():
        try:
            ir = ImageReader(str(logo_path))
            iw, ih = ir.getSize()
            scale = min(32 * mm / iw, 14 * mm / ih)
            logo_img = Image(str(logo_path), width=iw * scale, height=ih * scale)
        except Exception:
            logo_img = ""

    comp_name_en = _s(COMPANY.get("name_en", "NATTAYARAAT CO., LTD."))
    comp_addr = (
        f"{_s(COMPANY.get('address_line1', ''))} {_s(COMPANY.get('address_line2', ''))}<br/>"
        f"{_s(COMPANY.get('address_line3', ''))} | TAX ID: {_s(COMPANY.get('tax_id', ''))}"
    )

    # Box 1: Shipper vs TWB Number
    shipper_box = [
        Paragraph("<b>Shipper's Name and Address</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(shipper.replace("\n", "<br/>") if shipper else "—", styles["value"]),
    ]
    twb_no_box = [
        Paragraph("<b>TRUCK WAY BILL NUMBER</b>", styles["label_right"]),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>{twb_no}</b>", styles["value_bold_right"]),
    ]

    # Box 2: Consignee vs Issued By
    consignee_box = [
        Paragraph("<b>Consignee Name and Address</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(consignee.replace("\n", "<br/>") if consignee else "—", styles["value"]),
    ]
    
    comp_info_cells = [
        Paragraph(f"<b>{comp_name_en}</b>", styles["comp_name"]),
        Paragraph(comp_addr, styles["comp_addr"]),
    ]
    issued_by_content = [
        Paragraph("<b>Truck AWB Issued By</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Table([[logo_img or "", comp_info_cells]], colWidths=[32 * mm, 56 * mm]),
    ]

    # Box 3: Notify Party vs Delivery Agent
    notify_box = [
        Paragraph("<b>Notify Party</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(notify.replace("\n", "<br/>") if notify else "SAME AS CONSIGNEE", styles["value"]),
    ]
    delivery_box = [
        Paragraph("<b>Delivery Agent</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(delivery_agent.replace("\n", "<br/>") if delivery_agent else "—", styles["value"]),
    ]

    # Box 4: Booking Party vs Accounting Info
    booking_box = [
        Paragraph("<b>Booking Party</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(booking_party.replace("\n", "<br/>") if booking_party else "—", styles["value"]),
    ]
    acc_box = [
        Paragraph("<b>Accounting Information</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(accounting_info.replace("\n", "<br/>") if accounting_info else "—", styles["value"]),
    ]

    # Box 5: Origin vs Destination
    origin_box = [
        Paragraph("<b>Origin</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(origin, styles["value_bold"]),
    ]
    dest_box = [
        Paragraph("<b>Destination</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(destination, styles["value_bold"]),
    ]

    grid_data = [
        [shipper_box, twb_no_box],
        [consignee_box, issued_by_content],
        [notify_box, delivery_box],
        [booking_box, acc_box],
        [origin_box, dest_box],
    ]

    upper_grid = Table(grid_data, colWidths=[98 * mm, 98 * mm], rowHeights=[24 * mm, 26 * mm, 18 * mm, 16 * mm, 14 * mm])
    upper_grid.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8 * mm),
    ]))
    story.append(upper_grid)

    # =========================================================================
    # 3. PARTICULARS BANNER & 6-COLUMN CARGO TABLE
    # =========================================================================
    banner_table = Table(
        [[Paragraph("<b>PARTICULARS FURNISHED BY SHIPPER - CARRIER/AGENT NOT RESPONSIBLE</b>", styles["banner"])]],
        colWidths=[TOTAL_W],
        rowHeights=[5.5 * mm]
    )
    banner_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (-1, -1), BG_HEADER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(banner_table)

    cargo_headers = [
        Paragraph("<b>No of Pieces</b>", styles["table_head"]),
        Paragraph("<b>Gross Weight (kgs.)</b>", styles["table_head"]),
        Paragraph("<b>Vol. Wght (kgs.)</b>", styles["table_head"]),
        Paragraph("<b>Wght (kgs)</b>", styles["table_head"]),
        Paragraph("<b>Description</b>", styles["table_head"]),
        Paragraph("<b>Dimension</b>", styles["table_head"]),
    ]

    cargo_cells = [
        Paragraph(f"{package_qty} {package_type}", styles["table_cell_center"]),
        Paragraph(_num(gross_wt, 2), styles["table_cell_center"]),
        Paragraph(_num(vol_wt, 2), styles["table_cell_center"]),
        Paragraph(_num(actual_wt, 2), styles["table_cell_center"]),
        Paragraph(description.replace("\n", "<br/>"), styles["table_cell"]),
        Paragraph(dimension.replace("\n", "<br/>"), styles["table_cell_center"]),
    ]

    total_cells = [
        Paragraph("<b>Total</b>", styles["table_head"]),
        Paragraph(f"<b>{_num(gross_wt, 2)}</b>", styles["table_cell_center"]),
        Paragraph(f"<b>{_num(vol_wt, 2)}</b>", styles["table_cell_center"]),
        Paragraph(f"<b>{_num(actual_wt, 2)}</b>", styles["table_cell_center"]),
        Paragraph("", styles["table_cell"]),
        Paragraph("", styles["table_cell_center"]),
    ]

    cargo_table = Table(
        [cargo_headers, cargo_cells, total_cells],
        colWidths=[26 * mm, 30 * mm, 28 * mm, 26 * mm, 56 * mm, 30 * mm],
        rowHeights=[7 * mm, 26 * mm, 6.5 * mm]
    )
    cargo_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (0, 2), (-1, 2), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), BG_HEADER),
        ("BACKGROUND", (0, 2), (-1, 2), BG_HEADER),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]))
    story.append(cargo_table)

    # =========================================================================
    # 4. INVOICE DETAILS & CUSTOMER REF
    # =========================================================================
    inv_box = [
        Paragraph("<b>Invoice Details</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(invoice_details, styles["value"]),
    ]
    cust_ref_box = [
        Paragraph("<b>Customer Ref #</b>", styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph(customer_ref, styles["value"]),
    ]
    ref_table = Table([[inv_box, cust_ref_box]], colWidths=[98 * mm, 98 * mm], rowHeights=[14 * mm])
    ref_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]))
    story.append(ref_table)

    disc_table = Table(
        [[Paragraph("The particulars given above are as stated by shipper. The actual weight, measure, quantity, condition, content and value of the Goods are unknown to the Carrier.", styles["disclaimer"])]],
        colWidths=[TOTAL_W],
        rowHeights=[5 * mm]
    )
    disc_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(disc_table)

    # =========================================================================
    # 5. BOTTOM SUMMARY & DECLARATION
    # =========================================================================
    summary_cells = [
        Paragraph(f"<b>Move Type:</b> {move_type}", styles["summary_val"]),
        Spacer(1, 1.2 * mm),
        Paragraph(f"<b>Freight Charges:</b> {freight_charges}", styles["summary_val"]),
        Spacer(1, 1.2 * mm),
        Paragraph(f"<b>Duty and Other Charges:</b> {duty_charges}", styles["summary_val"]),
        Spacer(1, 1.2 * mm),
        Paragraph(f"<b>Origin Charges:</b> {origin_charges}", styles["summary_val"]),
        Spacer(1, 1.2 * mm),
        Paragraph(f"<b>Destination Charges:</b> {dest_charges}", styles["summary_val"]),
    ]

    stamp_path = Path("assets/company_stamp_blue.png")
    stamp_img = ""
    if stamp_path.exists():
        try:
            ir_s = ImageReader(str(stamp_path))
            sw, sh = ir_s.getSize()
            diag_mm = 1.7 * 25.4  # 43.18 mm
            aspect = sh / sw if sw > 0 else 1.0
            stamp_w = (diag_mm / ((1.0 + aspect**2)**0.5)) * mm
            stamp_h = stamp_w * aspect
            stamp_img = Image(str(stamp_path), width=stamp_w, height=stamp_h)
        except Exception:
            stamp_img = ""

    terms_text = (
        f"This is to confirm that I as the owner and the sender of the aforementioned shipment, acknowledge, "
        f"understood and agree to the terms and conditions stated and produced on the back of the waybill conditions "
        f"that limit liability and responsibility of {comp_name_en} in case of damage or loss is limited to USD 100 only, unless insured.<br/><br/>"
        f"Received by the Carrier, the Goods as specified above in apparent good order and condition unless otherwise states, to be transported to such place as agreed.<br/><br/>"
        f"The customer agrees the contents as appearing in TRUCK WAY BILL to be correct."
    )

    terms_box = [
        Paragraph(terms_text, styles["terms"]),
        Spacer(1, 2 * mm),
        Table([["Signature of Shipper / Agent: ____________________", stamp_img or ""]], colWidths=[65 * mm, 35 * mm])
    ]

    bottom_table = Table([[summary_cells, terms_box]], colWidths=[76 * mm, 120 * mm], rowHeights=[36 * mm])
    bottom_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
    ]))
    story.append(bottom_table)

    watermark_text = "" if approval_status in {"Approved", "Issued"} else approval_status.upper()
    doc.build(story, onFirstPage=lambda c, d: _draw_watermark(c, d, watermark_text) if watermark_text else None)
    return output_path
