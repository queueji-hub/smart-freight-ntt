"""
A4 Ocean Bill of Lading (HBL) PDF Generator.
100% Precision Match with International Standard Shipping Line Form Layout.
"""
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
)

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

BORDER_GREEN = colors.HexColor("#16A34A")  # Classic BL border styling
LABEL_GREEN = colors.HexColor("#15803D")
DARK_TEXT = colors.HexColor("#0F172A")


def _fmt(d) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%Y")
        except Exception:
            return d
    return d.strftime("%d-%b-%Y")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=16, textColor=LABEL_GREEN,
            alignment=TA_CENTER, spaceBefore=2, spaceAfter=2),
        "label": ParagraphStyle("l", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=7, textColor=LABEL_GREEN, leading=8),
        "label_b": ParagraphStyle("lb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=7, textColor=LABEL_GREEN, leading=8),
        "value": ParagraphStyle("v", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8, leading=10, textColor=DARK_TEXT),
        "value_b": ParagraphStyle("vb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8.5, leading=10.5, textColor=DARK_TEXT),
        "legal": ParagraphStyle("leg", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=5.5, leading=7, textColor=DARK_TEXT, alignment=TA_JUSTIFY),
        "center_bold": ParagraphStyle("cb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8, leading=10, alignment=TA_CENTER),
        "right_bold": ParagraphStyle("rb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8, leading=10, alignment=TA_RIGHT),
    }


def _header_grid(bl: Dict[str, Any], styles) -> Table:
    """Renders the top header grid (Shipper vs Company Logo & B/L No)."""
    bl_no = bl.get("bl_no") or bl.get("job_no") or "NATTA-LCHNAH2608003"
    
    # Shipper Block
    shipper_content = [
        Paragraph("Shipper", styles["label"]),
        Spacer(1, 1*mm),
        Paragraph(f"<b>{bl.get('shipper_name', bl.get('shipper', 'Y2J MACHINERY CO.,LTD.'))}</b>", styles["value_b"]),
        Paragraph(bl.get("shipper_address", "8/22 PAILOM SUB-DISTRICT BANGKRATUM DISTRICT,\nPHITSANULOK 65110"), styles["value"]),
    ]
    
    # Right Header Block (Company Logo + B/L No + Title)
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(logo_path)
        iw, ih = ir.getSize()
        scale = min(35*mm / iw, 18*mm / ih)
        logo = Image(logo_path, width=iw*scale, height=ih*scale)
    else:
        logo = Paragraph("<b>[LOGO]</b>", styles["value"])

    company_info = [
        Paragraph(f"<b>{COMPANY.get('name_en', 'NATTAYARAAT CO., LTD.')}</b>", styles["label_b"]),
        Paragraph(f'<font size="5.5">{COMPANY.get("address_full", "")}<br/>TAX ID: {COMPANY.get("tax_id", "")}</font>', styles["value"]),
    ]
    company_tbl = Table([[logo, company_info]], colWidths=[38*mm, 50*mm])
    company_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))

    right_header = [
        Paragraph(f'<b>B/L No. <font color="#15803D">{bl_no}</font></b>', styles["value_b"]),
        Spacer(1, 2*mm),
        company_tbl,
        Spacer(1, 2*mm),
        Paragraph("OCEAN BILL OF LADING", styles["title"]),
    ]
    
    tbl = Table([[shipper_content, right_header]], colWidths=[90*mm, 90*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return tbl


def _parties_grid(bl: Dict[str, Any], styles) -> Table:
    """Renders Consignee, Notify Party, and Delivery Agent Grid."""
    consignee_block = [
        Paragraph("Consignee", styles["label"]),
        Spacer(1, 1*mm),
        Paragraph(f"<b>{bl.get('consignee_name', bl.get('consignee', 'KUMIKI CO.,LTD.'))}</b>", styles["value_b"]),
        Paragraph(bl.get("consignee_address", "439 AZA UEYONABARU, YONABARU-CHO,\nOKINAWA 901-1302 JAPAN\nPHONE: (81) 98 945 3511\nFAX: (81) 98 946 2775"), styles["value"]),
    ]

    notify_block = [
        Paragraph("Notify Party", styles["label"]),
        Paragraph(bl.get("notify_party", "SAME AS CONSIGNEE"), styles["value_b"]),
    ]

    delivery_agent_block = [
        Paragraph("For Delivery of Goods Please Apply to", styles["label"]),
        Paragraph(bl.get("delivery_agent", "SAME AS CONSIGNEE / CARRIER AGENT"), styles["value"]),
    ]

    left_col = Table([[consignee_block], [notify_block]], colWidths=[90*mm], rowHeights=[22*mm, 14*mm])
    left_col.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))

    tbl = Table([[left_col, delivery_agent_block]], colWidths=[90*mm, 90*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
    ]))
    return tbl


def _routing_grid(bl: Dict[str, Any], styles) -> Table:
    """Renders Pre-Carriage, Vessel, POL, POD, and Delivery Place."""
    data = [
        [
            [Paragraph("Pre-Carriage by", styles["label"]), Paragraph(bl.get("pre_carriage", "—"), styles["value"])],
            [Paragraph("Place of Receipt", styles["label"]), Paragraph(bl.get("por", bl.get("pol", "LAEM CHABANG, THAILAND")), styles["value"])]
        ],
        [
            [Paragraph("Ocean Vessel/Voyage No.", styles["label"]), Paragraph(bl.get("vessel_voyage", f"{bl.get('vessel_name','SKY CHALLENGE')} {bl.get('voyage_no','V.2608N')}"), styles["value_b"])],
            [Paragraph("Port of Loading", styles["label"]), Paragraph(bl.get("pol", "LAEM CHABANG, THAILAND"), styles["value_b"])]
        ],
        [
            [Paragraph("Port of Discharge", styles["label"]), Paragraph(bl.get("pod", "NAHA, OKINAWA, JAPAN"), styles["value_b"])],
            [Paragraph("Place of Delivery", styles["label"]), Paragraph(bl.get("place_of_delivery", bl.get("pod", "NAHA, OKINAWA, JAPAN")), styles["value_b"])]
        ],
        [
            [Paragraph("Final Destination (For The Merchant's Reference Only)", styles["label"]), Paragraph(bl.get("final_destination", "—"), styles["value"])],
            ""
        ]
    ]

    tbl = Table([
        [data[0][0], data[0][1]],
        [data[1][0], data[1][1]],
        [data[2][0], data[2][1]],
        [data[3][0], ""]
    ], colWidths=[90*mm, 90*mm])

    tbl.setStyle(TableStyle([
        ("SPAN", (0, 3), (1, 3)),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    return tbl


def _cargo_table(bl: Dict[str, Any], styles) -> Table:
    """Renders 5-column Cargo Table matching standard BL specs."""
    headers = [
        Paragraph("Marks and Numbers<br/>Container & Seal Numbers", styles["label_b"]),
        Paragraph("No. of Packages", styles["label_b"]),
        Paragraph("Description of Packages and Goods<br/>Packages Forwarded by Shipper", styles["label_b"]),
        Paragraph("Gross Weight Kgs", styles["label_b"]),
        Paragraph("Measurement CBM", styles["label_b"]),
    ]

    marks_text = (
        f"{bl.get('marks_and_numbers', 'KM<br/>MADE IN THAILAND')}<br/><br/><br/>"
        f"<b>SHIPPED IN CONTAINER</b><br/>"
        f"PART OF CONTAINER NO. {bl.get('container_no', 'CAIU8226953')} / {bl.get('container_size', '40\'HQ')}<br/>"
        f"SEAL NUM: {bl.get('seal_no', 'M4912926')}"
    )

    desc_lines = [
        "<b>SAID TO CONTAINER(CY-CY)</b>",
        "<b>SHIPPER'S LOAD & COUNT & SEAL</b>",
        bl.get("commodity", "HARNESS SET FOR YT8000 (NO PROGRAM)\nINCINATION SENSOR WITH PROGRAM AND WIRING H\nHS CODE : 85443091\nHYD. CYL. BASE CUTTER LIFT\nHS CODE : 84122100\nHYD. GEAR MOTOR M31A \"GPM\"\nHYD. GEAR MOTOR M51A \"GPM\"\nHA CODE : 84122900\nMOUNTING & SILL PLATE YT7500\nSMALL TANK HYD. ON TOP W/A\nBASKET-V3.2-HAFT-R+L ASSY YT7500\nFUEL TANK WELDED ASSY CAP YT6500\nHS CODE : 84339090\nBOOSTER SEAT-YY30\nHS CODE : 83024290").replace("\n", "<br/>"),
        f"<br/>NET WEIGHT : {bl.get('net_weight_kg', '852.00')} KGS",
        f"<br/><b>{bl.get('freight_terms', 'FREIGHT PREPAID')}</b>",
        f"<br/><b>{bl.get('package_summary_caps', 'THREE PACKAGES ONLY')}</b>"
    ]
    desc_text = "<br/>".join(desc_lines)

    data = [
        headers,
        [
            Paragraph(marks_text, styles["value"]),
            Paragraph(str(bl.get("packages", "3 PACKAGES")), styles["value_b"]),
            Paragraph(desc_text, styles["value"]),
            Paragraph(f"<b>{bl.get('gross_weight_kg', '982.00')} KGS</b>", styles["value_b"]),
            Paragraph(f"<b>{bl.get('volume_cbm', '5.132')} CBM</b>", styles["value_b"]),
        ]
    ]

    tbl = Table(data, colWidths=[45*mm, 25*mm, 60*mm, 25*mm, 25*mm], rowHeights=[10*mm, 65*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (1,0), (1,-1), "LEFT"),
        ("ALIGN", (3,0), (-1,-1), "LEFT"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return tbl


def _legal_and_signature_grid(bl: Dict[str, Any], styles) -> Table:
    """Renders Freight Disbursement, Legal Carrier Terms, and Signature Box."""
    legal_text = (
        "RECEIVED by the Carrier the Goods as specified above in apparent good order and condition unless otherwise stated, to be "
        "transported to such place as agreed, authorized or permitted herein and subject to all the terms and conditions appearing "
        "on the front and back of this Bill of Lading to which the Merchant agrees by accepting this Bill of Lading, any local privileges "
        "and customs notwithstanding.<br/><br/>"
        "The particulars given below as stated by the shipper and the weight, measure, quantity, condition, contents and value of the "
        "goods are unknown to the Carrier.<br/><br/>"
        "IN WITNESS whereof (insert original) of Bill of Lading has been signed if not otherwise stated above, the same being "
        "accomplished, the other(s), if any, to be void. If required by the Carrier one (1) original Bill of Lading must be surrendered "
        "duly endorsed in exchange for the Goods or delivery order."
    )

    disbursement_headers = [
        Paragraph("Freight and<br/>Disbursements", styles["label"]),
        Paragraph("Rate at<br/>KGS/Tons", styles["label"]),
        Paragraph("Prepaid", styles["label"]),
        Paragraph("Collect", styles["label"]),
    ]
    
    # Left Disbursement Table
    disburse_tbl = Table([
        disbursement_headers,
        ["", "", "", ""],
        [Paragraph("Total", styles["label_b"]), "", "", ""]
    ], colWidths=[20*mm, 20*mm, 20*mm, 20*mm], rowHeights=[8*mm, 22*mm, 5*mm])
    disburse_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ]))

    right_legal = Paragraph(legal_text, styles["legal"])

    row1 = Table([[disburse_tbl, right_legal]], colWidths=[80*mm, 100*mm])
    row1.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ]))

    # Bottom Grid: Payable at / Issue Place & Date / Signature
    bot_left = [
        [Paragraph("Freight payable at", styles["label"]), Paragraph("Place and date of issue", styles["label"])],
        [Paragraph(bl.get("freight_payable_at", "BANGKOK, THAILAND"), styles["value"]), Paragraph(bl.get("issue_place_date", "BANGKOK, THAILAND / " + _fmt(bl.get("issue_date", date.today()))), styles["value"])],
        [Paragraph("Number of original B/Ls", styles["label"]), Paragraph("Signed on behalf of<br/>the Carrier :", styles["label"])],
        [Paragraph(bl.get("original_bl_count", "3 (THREE)"), styles["value_b"]), Paragraph(f"<br/><br/>By ___________________________<br/><b>{COMPANY.get('name_en')}</b><br/>As Agent Only", styles["value"])]
    ]

    bot_tbl = Table(bot_left, colWidths=[90*mm, 90*mm])
    bot_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER_GREEN),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))

    wrapper = Table([[row1], [bot_tbl]], colWidths=[180*mm])
    wrapper.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return wrapper


def _draft_watermark_canvas(canvas, doc, is_draft=True):
    """Draws diagonal semi-transparent 'DRAFT' watermark if status is not ISSUED."""
    canvas.saveState()
    if is_draft:
        canvas.setFont(THAI_FONT_BOLD, 72)
        canvas.setFillColor(colors.HexColor("#22C55E"), alpha=0.15)  # Soft green DRAFT watermark matching sample
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, "DRAFT")

    # Footer Page Number
    canvas.setFont(THAI_FONT, 7)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(15 * mm, 6 * mm, "Smart Freight NTT, — Enterprise Bill of Lading Engine")
    canvas.drawRightString(A4[0] - 15 * mm, 6 * mm, f"Page {doc.page} of 1")
    canvas.restoreState()


def generate_bl_pdf(shipment: Dict[str, Any], output_path: str = None) -> str:
    """Generate Bill of Lading PDF with 100% Precision Matching Sample Form."""
    if output_path is None:
        bl_no = shipment.get("bl_no") or shipment.get("job_no", "BL")
        output_path = str(Path(OUTPUT_DIR) / f"BL_{bl_no}.pdf")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=10*mm, bottomMargin=10*mm,
        title=f"B/L {shipment.get('bl_no','')}",
        author=COMPANY["name"],
    )
    styles = _styles()
    story = []
    
    story.append(_header_grid(shipment, styles))
    story.append(_parties_grid(shipment, styles))
    story.append(_routing_grid(shipment, styles))
    story.append(_cargo_table(shipment, styles))
    story.append(_legal_and_signature_grid(shipment, styles))
    
    is_draft = str(shipment.get("status", "")).upper().strip() != "ISSUED"

    doc.build(
        story,
        onFirstPage=lambda c, d: _draft_watermark_canvas(c, d, is_draft=is_draft),
        onLaterPages=lambda c, d: _draft_watermark_canvas(c, d, is_draft=is_draft)
    )
    return output_path
