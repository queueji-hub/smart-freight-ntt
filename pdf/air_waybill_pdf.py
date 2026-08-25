"""Pure ReportLab IATA House Air Waybill (HAWB) PDF generator.

Layout matches the standard IATA 45-box Air Waybill specification:
- Header: Airline MAWB Prefix & HAWB Number
- Box 1: Shipper Name, Address & Account No.
- Box 2: Not Negotiable Air Waybill Issued By (NATTAYARAAT Logo, Address, Tax ID, Contacts)
- Box 3: Consignee Name, Address & Account No.
- Box 4: Agent's IATA Code & Account No.
- Box 5: Airport of Departure & Reference to Routing
- Box 6: Notify Party
- Box 7: Accounting Information
- Routing Grid: To / By First Carrier / To / By / Currency / CHGS Code / WT-VAL / Other / Declared Value Carriage / Customs
- Flight/Date / Airport of Destination / Amount of Insurance
- Handling Information & SCI (Special Customs Information)
- 14-Column Rating Grid: Pieces, Gross Weight, kg/lb, Rate Class, Item No., Chargeable Weight, Rate/Charge, Total, Nature & Quantity of Goods
- Prepaid / Collect Summary Matrix
- Other Charges Breakdown
- Shipper Certification & Signature
- Executed on Date/Place & Issuing Carrier Signature with Company Stamp
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

BORDER_COLOR = colors.HexColor("#0F172A")
BORDER_LIGHT = colors.HexColor("#334155")
TEXT_DARK = colors.HexColor("#0F172A")
LABEL_COLOR = colors.HexColor("#334155")
BG_HEADER = colors.HexColor("#F8FAFC")
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
        "hawb_top": ParagraphStyle("awb_top", parent=base["Normal"], fontName=FONT_BOLD, fontSize=11, leading=13, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "mawb_top": ParagraphStyle("awb_mtop", parent=base["Normal"], fontName=FONT_BOLD, fontSize=11, leading=13, alignment=TA_LEFT, textColor=TEXT_DARK),
        "title_sub": ParagraphStyle("awb_sub", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7, leading=8.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "box_num": ParagraphStyle("awb_bnum", parent=base["Normal"], fontName=FONT_BOLD, fontSize=5.0, leading=6.0, textColor=LABEL_COLOR),
        "label": ParagraphStyle("awb_label", parent=base["Normal"], fontName=FONT_BOLD, fontSize=5.5, leading=6.5, textColor=LABEL_COLOR),
        "label_center": ParagraphStyle("awb_label_c", parent=base["Normal"], fontName=FONT_BOLD, fontSize=5.5, leading=6.5, alignment=TA_CENTER, textColor=LABEL_COLOR),
        "value": ParagraphStyle("awb_value", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8.2, textColor=TEXT_DARK),
        "value_bold": ParagraphStyle("awb_val_b", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.2, leading=8.8, textColor=TEXT_DARK),
        "value_center": ParagraphStyle("awb_val_c", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "comp_name": ParagraphStyle("awb_cname", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.0, leading=9.5, textColor=TEXT_DARK),
        "comp_addr": ParagraphStyle("awb_caddr", parent=base["Normal"], fontName=FONT, fontSize=5.5, leading=6.8, textColor=TEXT_DARK),
        "comp_clause": ParagraphStyle("awb_cclause", parent=base["Normal"], fontName=FONT, fontSize=4.8, leading=5.8, textColor=LABEL_COLOR),
        "table_head": ParagraphStyle("awb_thead", parent=base["Normal"], fontName=FONT_BOLD, fontSize=5.5, leading=6.8, alignment=TA_CENTER, textColor=LABEL_COLOR),
        "table_cell": ParagraphStyle("awb_tcell", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8.2, textColor=TEXT_DARK),
        "table_cell_center": ParagraphStyle("awb_tcell_c", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "cert_text": ParagraphStyle("awb_cert", parent=base["Normal"], fontName=FONT, fontSize=4.8, leading=6.0, alignment=TA_JUSTIFY, textColor=TEXT_DARK),
        "summary_lbl": ParagraphStyle("awb_slbl", parent=base["Normal"], fontName=FONT_BOLD, fontSize=5.5, leading=7.0, textColor=LABEL_COLOR),
        "summary_val": ParagraphStyle("awb_sval", parent=base["Normal"], fontName=FONT, fontSize=6.5, leading=8.0, alignment=TA_RIGHT, textColor=TEXT_DARK),
    }


def _draw_watermark(canvas, doc, watermark_text: str = "COPY"):
    canvas.saveState()
    canvas.setFont(FONT_BOLD, 68)
    canvas.setFillColor(WATERMARK_COLOR)
    canvas.translate(A4[0] / 2, A4[1] * 0.42)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, watermark_text)
    canvas.restoreState()


def generate_air_waybill_pdf(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    bl = dict(payload.get("bl") or {})
    job = dict(payload.get("job") or {})
    booking = dict(payload.get("booking") or {})
    styles = _styles()

    hawb_no = _s(bl.get("hawb_no") or bl.get("bl_no"), "HAWB-2608-0001")
    mawb_no = _s(bl.get("mawb_no") or booking.get("mawb_no") or job.get("mbl_no") or "217-89012345")
    approval_status = _s(bl.get("approval_status") or bl.get("status"), "Draft")

    shipper = _s(bl.get("shipper"))
    shipper_acct = _s(bl.get("exporter_account_no") or job.get("customer_reference") or "—")
    consignee = _s(bl.get("consignee"))
    consignee_acct = _s(bl.get("consignee_account_no") or "—")
    notify = _s(bl.get("notify_party"), "SAME AS CONSIGNEE")

    iata_code = _s(bl.get("iata_code"), "33-4-7890/0014")
    agent_acct = _s(bl.get("agent_account_no"), "BKK-0988")
    accounting_info = _s(bl.get("accounting_info"), "FREIGHT PREPAID / ISSUED AS PER AGREEMENT")

    pol = _s(bl.get("airport_departure") or bl.get("port_of_loading") or job.get("pol") or "BKK / BANGKOK")
    pod = _s(bl.get("airport_destination") or bl.get("port_of_discharge") or job.get("pod") or "SIN / SINGAPORE")
    first_carrier = _s(bl.get("first_carrier") or job.get("carrier") or "THAI AIRWAYS (TG)")
    flight_no = _s(bl.get("flight_no") or booking.get("flight_no") or "TG 401")
    flight_date = _s(bl.get("flight_date") or bl.get("etd") or "2026-08-25")

    curr = _s(bl.get("currency") or "USD")
    chgs_code = _s(bl.get("chgs_code") or ("PP" if "PREPAID" in str(bl.get("freight_term", "PREPAID")).upper() else "CC"))
    wt_val_ppd = _s(bl.get("wt_val_ppd") or ("P" if chgs_code == "PP" else ""))
    wt_val_coll = _s(bl.get("wt_val_coll") or ("C" if chgs_code == "CC" else ""))
    other_ppd = _s(bl.get("other_ppd") or ("P" if chgs_code == "PP" else ""))
    other_coll = _s(bl.get("other_coll") or ("C" if chgs_code == "CC" else ""))

    decl_val_carriage = _s(bl.get("declared_value_carriage"), "N.V.D.")
    decl_val_customs = _s(bl.get("declared_value_customs"), "N.C.V.")
    amount_insurance = _s(bl.get("amount_of_insurance"), "XXX")

    handling_info = _s(bl.get("handling_info"), "NO SPECIAL HANDLING REQUIRED / GENERAL CARGO")
    sci = _s(bl.get("sci"), "TH-EXP")

    package_qty = _s(bl.get("package_qty")) or "1"
    gross_wt = _s(bl.get("gross_weight")) or "100.0"
    chargeable_wt = _s(bl.get("chargeable_weight")) or gross_wt
    rate_class = _s(bl.get("rate_class"), "Q")
    item_no = _s(bl.get("commodity_item_no") or bl.get("hs_code") or "—")
    rate_charge = _s(bl.get("rate_charge")) or "AS AGREED"
    total_charge = _s(bl.get("total_charge")) or "AS AGREED"
    goods_nature = _s(bl.get("description_of_goods") or job.get("commodity") or "SAID TO CONTAIN GENERAL CARGO")

    # Output path
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"AWB_{hawb_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=7 * mm,
        rightMargin=7 * mm,
        topMargin=7 * mm,
        bottomMargin=7 * mm,
        title=f"Air Waybill {hawb_no}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )

    story = []

    # =========================================================================
    # 1. TOP HEADER (MAWB Prefix vs Document Title vs HAWB Number)
    # =========================================================================
    top_left = [Paragraph(f"<b>{mawb_no}</b>", styles["mawb_top"])]
    top_mid = [Paragraph("<b>HOUSE AIR WAYBILL<br/>Not Negotiable</b>", styles["title_sub"])]
    top_right = [Paragraph(f"<b>{hawb_no}</b>", styles["hawb_top"])]

    top_table = Table([[top_left, top_mid, top_right]], colWidths=[65 * mm, 66 * mm, 65 * mm])
    top_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
    ]))
    story.append(top_table)

    # =========================================================================
    # 2. UPPER 2-COLUMN GRID (Boxes 1 to 7)
    # =========================================================================
    logo_path = COMPANY.get("logo_path")
    logo_img = ""
    if logo_path and Path(str(logo_path)).exists():
        try:
            ir = ImageReader(str(logo_path))
            iw, ih = ir.getSize()
            scale = min(30 * mm / iw, 13 * mm / ih)
            logo_img = Image(str(logo_path), width=iw * scale, height=ih * scale)
        except Exception:
            logo_img = ""

    comp_name_en = _s(COMPANY.get("name_en", "NATTAYARAAT CO., LTD."))
    comp_addr = (
        f"{_s(COMPANY.get('address_line1', ''))} {_s(COMPANY.get('address_line2', ''))}<br/>"
        f"{_s(COMPANY.get('address_line3', ''))} | TAX ID: {_s(COMPANY.get('tax_id', ''))}"
    )

    # Box 1: Shipper Name, Address & Account
    shipper_box = [
        Paragraph("<b>Shipper's Name and Address</b>", styles["label"]),
        Spacer(1, 0.6 * mm),
        Paragraph(shipper.replace("\n", "<br/>") if shipper else "—", styles["value"]),
        Spacer(1, 1.2 * mm),
        Paragraph(f"<b>Shipper's Account Number:</b> {shipper_acct}", styles["label"]),
    ]

    # Box 2: Issued By
    comp_info_cells = [
        Paragraph(f"<b>{comp_name_en}</b>", styles["comp_name"]),
        Paragraph(comp_addr, styles["comp_addr"]),
    ]
    issued_by_content = [
        Paragraph("<b>Not Negotiable Air Waybill Issued by</b>", styles["label"]),
        Spacer(1, 0.6 * mm),
        Table([[logo_img or "", comp_info_cells]], colWidths=[30 * mm, 64 * mm]),
        Spacer(1, 0.6 * mm),
        Paragraph("Copies 1, 2 and 3 of this Air Waybill are originals and have the same validity.", styles["comp_clause"]),
    ]

    # Box 3: Consignee Name, Address & Account
    consignee_box = [
        Paragraph("<b>Consignee's Name and Address</b>", styles["label"]),
        Spacer(1, 0.6 * mm),
        Paragraph(consignee.replace("\n", "<br/>") if consignee else "—", styles["value"]),
        Spacer(1, 1.2 * mm),
        Paragraph(f"<b>Consignee's Account Number:</b> {consignee_acct}", styles["label"]),
    ]

    # Box 4 & 5: Agent IATA & Departure
    agent_box = [
        Paragraph("<b>Agent's IATA Code:</b> " + iata_code + " &nbsp;&nbsp;&nbsp;&nbsp; <b>Account No.:</b> " + agent_acct, styles["label"]),
        Spacer(1, 0.8 * mm),
        Paragraph("<b>Airport of Departure (Addr. of First Carrier) and Requested Routing:</b>", styles["label"]),
        Paragraph(f"<b>{pol}</b> via {first_carrier}", styles["value_bold"]),
    ]

    # Box 6: Notify Party
    notify_box = [
        Paragraph("<b>Notify Party</b>", styles["label"]),
        Spacer(1, 0.6 * mm),
        Paragraph(notify.replace("\n", "<br/>") if notify else "SAME AS CONSIGNEE", styles["value"]),
    ]

    # Box 7: Accounting Information
    acc_box = [
        Paragraph("<b>Accounting Information</b>", styles["label"]),
        Spacer(1, 0.6 * mm),
        Paragraph(accounting_info.replace("\n", "<br/>") if accounting_info else "—", styles["value"]),
    ]

    upper_grid = Table([
        [shipper_box, issued_by_content],
        [consignee_box, agent_box],
        [notify_box, acc_box],
    ], colWidths=[98 * mm, 98 * mm], rowHeights=[26 * mm, 24 * mm, 18 * mm])

    upper_grid.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]))
    story.append(upper_grid)

    # =========================================================================
    # 3. ROUTING & FINANCIAL TERMS MATRIX (Boxes 8-23)
    # =========================================================================
    routing_h1 = [
        Paragraph("<b>To</b>", styles["label_center"]),
        Paragraph("<b>By First Carrier</b>", styles["label_center"]),
        Paragraph("<b>To</b>", styles["label_center"]),
        Paragraph("<b>By</b>", styles["label_center"]),
        Paragraph("<b>To</b>", styles["label_center"]),
        Paragraph("<b>By</b>", styles["label_center"]),
        Paragraph("<b>Currency</b>", styles["label_center"]),
        Paragraph("<b>CHGS</b>", styles["label_center"]),
        Paragraph("<b>WT/VAL<br/>PPD | COLL</b>", styles["label_center"]),
        Paragraph("<b>Other<br/>PPD | COLL</b>", styles["label_center"]),
        Paragraph("<b>Declared Value<br/>for Carriage</b>", styles["label_center"]),
        Paragraph("<b>Declared Value<br/>for Customs</b>", styles["label_center"]),
    ]

    dest_3letter = (pod.split("/")[0] if "/" in pod else pod)[:3].strip().upper()
    carrier_code = (first_carrier.split("(")[1].replace(")", "") if "(" in first_carrier else first_carrier[:2]).strip().upper()

    routing_v1 = [
        Paragraph(dest_3letter, styles["value_center"]),
        Paragraph(carrier_code, styles["value_center"]),
        Paragraph("", styles["value_center"]),
        Paragraph("", styles["value_center"]),
        Paragraph("", styles["value_center"]),
        Paragraph("", styles["value_center"]),
        Paragraph(curr, styles["value_center"]),
        Paragraph(chgs_code, styles["value_center"]),
        Paragraph(f"{wt_val_ppd} | {wt_val_coll}", styles["value_center"]),
        Paragraph(f"{other_ppd} | {other_coll}", styles["value_center"]),
        Paragraph(decl_val_carriage, styles["value_center"]),
        Paragraph(decl_val_customs, styles["value_center"]),
    ]

    r_widths = [14 * mm, 22 * mm, 12 * mm, 12 * mm, 12 * mm, 12 * mm, 16 * mm, 14 * mm, 18 * mm, 18 * mm, 23 * mm, 23 * mm]
    routing_table_1 = Table([routing_h1, routing_v1], colWidths=r_widths, rowHeights=[6.5 * mm, 6.5 * mm])
    routing_table_1.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (-1, 0), BG_HEADER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(routing_table_1)

    # Row 2: Airport Dest vs Flight/Date vs Insurance
    dest_box = [
        Paragraph("<b>Airport of Destination</b>", styles["label"]),
        Paragraph(f"<b>{pod}</b>", styles["value_bold"]),
    ]
    flight_box = [
        Paragraph("<b>Flight / Date</b>", styles["label"]),
        Paragraph(f"<b>{flight_no} / {flight_date}</b>", styles["value_bold"]),
    ]
    ins_box = [
        Paragraph("<b>Amount of Insurance</b>", styles["label"]),
        Paragraph(amount_insurance, styles["value"]),
    ]
    ins_table = Table([[dest_box, flight_box, ins_box]], colWidths=[70 * mm, 66 * mm, 60 * mm], rowHeights=[10 * mm])
    ins_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
    ]))
    story.append(ins_table)

    # Row 3: Handling Info vs SCI
    handling_box = [
        Paragraph("<b>Handling Information</b>", styles["label"]),
        Spacer(1, 0.5 * mm),
        Paragraph(handling_info, styles["value"]),
    ]
    sci_box = [
        Paragraph("<b>SCI</b>", styles["label"]),
        Spacer(1, 0.5 * mm),
        Paragraph(sci, styles["value_bold"]),
    ]
    sci_table = Table([[handling_box, sci_box]], colWidths=[156 * mm, 40 * mm], rowHeights=[10 * mm])
    sci_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
    ]))
    story.append(sci_table)

    # =========================================================================
    # 4. 14-COLUMN CARGO & RATING GRID (Boxes 24-32)
    # =========================================================================
    cargo_headers = [
        Paragraph("<b>No. of Pieces<br/>RCP</b>", styles["table_head"]),
        Paragraph("<b>Gross<br/>Weight</b>", styles["table_head"]),
        Paragraph("<b>kg /<br/>lb</b>", styles["table_head"]),
        Paragraph("<b>Rate<br/>Class</b>", styles["table_head"]),
        Paragraph("<b>Commodity<br/>Item No.</b>", styles["table_head"]),
        Paragraph("<b>Chargeable<br/>Weight</b>", styles["table_head"]),
        Paragraph("<b>Rate /<br/>Charge</b>", styles["table_head"]),
        Paragraph("<b>Total</b>", styles["table_head"]),
        Paragraph("<b>Nature and Quantity of Goods<br/>(incl. Dimensions or Volume)</b>", styles["table_head"]),
    ]

    cargo_cells = [
        Paragraph(str(package_qty), styles["table_cell_center"]),
        Paragraph(_num(gross_wt, 2), styles["table_cell_center"]),
        Paragraph("K", styles["table_cell_center"]),
        Paragraph(rate_class, styles["table_cell_center"]),
        Paragraph(item_no, styles["table_cell_center"]),
        Paragraph(_num(chargeable_wt, 2), styles["table_cell_center"]),
        Paragraph(rate_charge, styles["table_cell_center"]),
        Paragraph(total_charge, styles["table_cell_center"]),
        Paragraph(goods_nature.replace("\n", "<br/>"), styles["table_cell"]),
    ]

    total_row = [
        Paragraph(f"<b>{package_qty}</b>", styles["table_head"]),
        Paragraph(f"<b>{_num(gross_wt, 2)}</b>", styles["table_head"]),
        Paragraph("<b>K</b>", styles["table_head"]),
        Paragraph("", styles["table_head"]),
        Paragraph("", styles["table_head"]),
        Paragraph(f"<b>{_num(chargeable_wt, 2)}</b>", styles["table_head"]),
        Paragraph("", styles["table_head"]),
        Paragraph(f"<b>{total_charge}</b>", styles["table_head"]),
        Paragraph("<b>TOTAL CARGO CONSIGNMENT</b>", styles["table_head"]),
    ]

    c_widths = [16 * mm, 18 * mm, 10 * mm, 12 * mm, 18 * mm, 20 * mm, 20 * mm, 22 * mm, 60 * mm]
    cargo_table = Table([cargo_headers, cargo_cells, total_row], colWidths=c_widths, rowHeights=[8 * mm, 24 * mm, 6.5 * mm])
    cargo_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (-1, 0), BG_HEADER),
        ("BACKGROUND", (0, 2), (-1, 2), BG_HEADER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (0, 2), (-1, 2), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
    ]))
    story.append(cargo_table)

    # =========================================================================
    # 5. PREPAID / COLLECT SUMMARY & CERTIFICATION (Boxes 33-45)
    # =========================================================================
    fee_grid_data = [
        [Paragraph("<b>Prepaid</b>", styles["summary_lbl"]), Paragraph("<b>Weight Charge</b>", styles["summary_lbl"]), Paragraph("<b>Collect</b>", styles["summary_lbl"])],
        [Paragraph("AS AGREED" if chgs_code == "PP" else "—", styles["summary_val"]), Paragraph("Valuation Charge", styles["summary_lbl"]), Paragraph("AS AGREED" if chgs_code == "CC" else "—", styles["summary_val"])],
        [Paragraph("—", styles["summary_val"]), Paragraph("Tax", styles["summary_lbl"]), Paragraph("—", styles["summary_val"])],
        [Paragraph("—", styles["summary_val"]), Paragraph("Total Other Charges Due Agent", styles["summary_lbl"]), Paragraph("—", styles["summary_val"])],
        [Paragraph("—", styles["summary_val"]), Paragraph("Total Other Charges Due Carrier", styles["summary_lbl"]), Paragraph("—", styles["summary_val"])],
        [Paragraph("<b>AS AGREED</b>" if chgs_code == "PP" else "—", styles["summary_val"]), Paragraph("<b>Total Prepaid / Collect</b>", styles["summary_lbl"]), Paragraph("<b>AS AGREED</b>" if chgs_code == "CC" else "—", styles["summary_val"])],
    ]

    fee_table = Table(fee_grid_data, colWidths=[28 * mm, 42 * mm, 28 * mm], rowHeights=[4.8 * mm] * 6)
    fee_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5 * mm),
    ]))

    other_charges_box = [
        Paragraph("<b>Other Charges:</b>", styles["label"]),
        Paragraph("MYC (Fuel): AS AGREED | SCC (Security): AS AGREED | CGC (Terminal): AS AGREED", styles["value"]),
    ]

    cert_text = (
        "Shipper certifies that the particulars on the face hereof are correct and that insofar as any part of the "
        "consignment contains dangerous goods, such part is properly described by name and is in proper condition for "
        "carriage by air according to the applicable Dangerous Goods Regulations."
    )

    stamp_path = Path("assets/company_stamp_blue.png")
    stamp_img = ""
    if stamp_path.exists():
        try:
            ir_s = ImageReader(str(stamp_path))
            sw, sh = ir_s.getSize()
            s_scale = min(26 * mm / sw, 16 * mm / sh)
            stamp_img = Image(str(stamp_path), width=sw * s_scale, height=sh * s_scale)
        except Exception:
            stamp_img = ""

    exec_date = str(bl.get("bl_date") or date.today().strftime("%Y-%m-%d"))
    exec_place = _s(bl.get("place_of_issue"), "BANGKOK, THAILAND")

    right_cert_content = [
        Table([[other_charges_box]], colWidths=[94 * mm]),
        Spacer(1, 1 * mm),
        Paragraph(cert_text, styles["cert_text"]),
        Spacer(1, 1.5 * mm),
        Paragraph("<b>Signature of Shipper or his Agent:</b> ____________________", styles["label"]),
        Spacer(1, 1.5 * mm),
        Table([
            [
                Paragraph(f"<b>Executed on:</b> {exec_date}<br/><b>at:</b> {exec_place}<br/><b>Signature of Issuing Carrier:</b>", styles["label"]),
                stamp_img or ""
            ]
        ], colWidths=[62 * mm, 32 * mm])
    ]

    bottom_matrix = Table([[fee_table, right_cert_content]], colWidths=[98 * mm, 98 * mm], rowHeights=[36 * mm])
    bottom_matrix.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]))
    story.append(bottom_matrix)

    watermark_text = "" if approval_status in {"Approved", "Issued"} else approval_status.upper()
    doc.build(story, onFirstPage=lambda c, d: _draw_watermark(c, d, watermark_text) if watermark_text else None)
    return output_path
