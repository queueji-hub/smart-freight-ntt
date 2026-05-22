"""A4 Bill of Lading (B/L) PDF generator."""
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

BRAND_BLUE = colors.HexColor("#1F4E9E")
BRAND_DARK = colors.HexColor("#0E2A47")
HEADER_GREY = colors.HexColor("#E5E7EB")


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
            fontName=THAI_FONT_BOLD, fontSize=22, textColor=BRAND_DARK,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=2),
        "subtitle": ParagraphStyle("st", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=10, textColor=colors.grey,
            alignment=TA_CENTER, spaceAfter=8),
        "label": ParagraphStyle("l", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8,
            textColor=BRAND_BLUE),
        "value": ParagraphStyle("v", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, leading=11),
        "value_b": ParagraphStyle("vb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=10),
        "body": ParagraphStyle("b", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, leading=12),
        "small": ParagraphStyle("s", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=7, leading=9),
    }


def _box(label, value, styles, w_label=30*mm, h=18*mm):
    """Render a labeled box (like B/L form fields)."""
    inner = [
        Paragraph(label, styles["label"]),
        Paragraph(value or "—", styles["value"]),
    ]
    return inner


def _header(styles, bl):
    """B/L Header with title and B/L No."""
    bl_no = bl.get("bl_no") or bl.get("job_no") or "—"
    
    # Right side info: BL No, Booking No, Job No
    right_info = Table([
        [Paragraph("<b>B/L No.</b>", styles["label"])],
        [Paragraph(f"<b>{bl_no}</b>", styles["value_b"])],
        [Spacer(1, 2*mm)],
        [Paragraph("<b>Booking No.</b>", styles["label"])],
        [Paragraph(bl.get("booking_no", "") or "—", styles["value"])],
    ], colWidths=[60*mm])
    right_info.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, BRAND_DARK),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 2),
    ]))
    
    title_block = [
        Paragraph(f"<b>{COMPANY['name']}</b>", styles["value_b"]),
        Spacer(1, 4*mm),
        Paragraph("BILL OF LADING", styles["title"]),
        Spacer(1, 1*mm),
        Paragraph("(For combined transport or port to port)", styles["subtitle"]),
    ]
    
    tbl = Table([[title_block, right_info]], colWidths=[120*mm, 60*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return tbl


def _parties_table(bl, styles):
    """Shipper / Consignee / Notify Party 3-row block."""
    data = [
        [Paragraph("<b>SHIPPER (EXPORTER)</b>", styles["label"]),
         Paragraph(bl.get("shipper", "") or "—", styles["value"])],
        [Paragraph("<b>CONSIGNEE</b>", styles["label"]),
         Paragraph(bl.get("consignee", "") or "—", styles["value"])],
        [Paragraph("<b>NOTIFY PARTY</b>", styles["label"]),
         Paragraph(bl.get("notify_party", "") or "—", styles["value"])],
    ]
    tbl = Table(data, colWidths=[40*mm, 140*mm], rowHeights=[20*mm]*3)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOX", (0,0), (-1,-1), 1, BRAND_DARK),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BRAND_DARK),
    ]))
    return tbl


def _vessel_table(bl, styles):
    """Vessel / Voyage / Routing block."""
    data = [
        [Paragraph("<b>VESSEL</b>", styles["label"]),
         Paragraph("<b>VOYAGE NO.</b>", styles["label"]),
         Paragraph("<b>PORT OF LOADING</b>", styles["label"]),
         Paragraph("<b>PORT OF DISCHARGE</b>", styles["label"])],
        [Paragraph(bl.get("m_vessel", "") or "—", styles["value"]),
         Paragraph(bl.get("voyage_no", "") or "—", styles["value"]),
         Paragraph(bl.get("pol", "") or "—", styles["value"]),
         Paragraph(bl.get("pod", "") or "—", styles["value"])],
        [Paragraph("<b>PLACE OF RECEIPT</b>", styles["label"]),
         Paragraph("<b>PLACE OF DELIVERY</b>", styles["label"]),
         Paragraph("<b>FEEDER VESSEL</b>", styles["label"]),
         Paragraph("<b>CARRIER</b>", styles["label"])],
        [Paragraph(bl.get("por", "") or "—", styles["value"]),
         Paragraph(bl.get("final_destination", "") or "—", styles["value"]),
         Paragraph(bl.get("feeder", "") or "—", styles["value"]),
         Paragraph(bl.get("carrier", "") or "—", styles["value"])],
    ]
    tbl = Table(data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BACKGROUND", (0,0), (-1,0), HEADER_GREY),
        ("BACKGROUND", (0,2), (-1,2), HEADER_GREY),
        ("BOX", (0,0), (-1,-1), 1, BRAND_DARK),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BRAND_DARK),
    ]))
    return tbl


def _cargo_table(bl, styles):
    """Cargo description block."""
    data = [
        [
            Paragraph("<b>MARKS & NUMBERS<br/>(Container/Seal)</b>", styles["label"]),
            Paragraph("<b>NO. OF<br/>PACKAGES</b>", styles["label"]),
            Paragraph("<b>DESCRIPTION OF GOODS</b>", styles["label"]),
            Paragraph("<b>GROSS WEIGHT</b>", styles["label"]),
            Paragraph("<b>MEASUREMENT</b>", styles["label"]),
        ],
        [
            Paragraph(
                f"Container: {bl.get('container_no','—')}<br/>"
                f"Seal: {bl.get('seal_no','—')}<br/>"
                f"Size: {bl.get('container_size','—')}",
                styles["small"]),
            Paragraph(bl.get("quantity", "") or bl.get("full_or_half", "") or "—",
                      styles["value"]),
            Paragraph(bl.get("commodity", "") or "—", styles["value"]),
            Paragraph(bl.get("weight_origin", "") or "—", styles["value"]),
            Paragraph(bl.get("weight_port", "") or "—", styles["value"]),
        ],
    ]
    tbl = Table(data, colWidths=[40*mm, 25*mm, 55*mm, 30*mm, 30*mm],
                 rowHeights=[None, 50*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BACKGROUND", (0,0), (-1,0), HEADER_GREY),
        ("BOX", (0,0), (-1,-1), 1, BRAND_DARK),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BRAND_DARK),
    ]))
    return tbl


def _bottom_block(bl, styles):
    """Freight & charges + Place/date issued."""
    data = [
        [Paragraph("<b>FREIGHT & CHARGES</b>", styles["label"]),
         Paragraph("<b>PLACE & DATE OF ISSUE</b>", styles["label"])],
        [Paragraph(
            f"Freight: {bl.get('freight_terms', 'Prepaid')}<br/>"
            f"Cargo Type: {bl.get('cargo_type', '—')}<br/>"
            f"Closing Time: {bl.get('closing_time', '—')}",
            styles["value"]),
         Paragraph(
            f"Place: Bangkok, Thailand<br/>"
            f"Date: {_fmt(bl.get('etd') or date.today())}<br/>"
            f"Number of original B/L(s): <b>3 (THREE)</b>",
            styles["value"])],
    ]
    tbl = Table(data, colWidths=[90*mm, 90*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BACKGROUND", (0,0), (-1,0), HEADER_GREY),
        ("BOX", (0,0), (-1,-1), 1, BRAND_DARK),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BRAND_DARK),
    ]))
    return tbl


def _signature_block(styles):
    """Carrier signature block."""
    data = [
        [Paragraph("<b>SIGNED FOR THE CARRIER</b>", styles["label"])],
        [Spacer(1, 18*mm)],
        [Paragraph("_" * 35, styles["body"])],
        [Paragraph(f"<b>{COMPANY['name']}</b>", styles["body"])],
        [Paragraph(f"As agent for the Carrier", styles["small"])],
    ]
    tbl = Table(data, colWidths=[180*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOX", (0,0), (-1,-1), 1, BRAND_DARK),
        ("ALIGN", (0,2), (0,-1), "RIGHT"),
    ]))
    return tbl


def generate_bl_pdf(shipment: Dict[str, Any], output_path: str = None) -> str:
    """Generate Bill of Lading PDF."""
    if output_path is None:
        bl_no = shipment.get("bl_no") or shipment.get("job_no", "BL")
        output_path = str(Path(OUTPUT_DIR) / f"BL_{bl_no}.pdf")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"B/L {shipment.get('bl_no','')}",
        author=COMPANY["name"],
    )
    styles = _styles()
    story = []
    
    story.append(_header(styles, shipment))
    story.append(Spacer(1, 4*mm))
    story.append(_parties_table(shipment, styles))
    story.append(Spacer(1, 2*mm))
    story.append(_vessel_table(shipment, styles))
    story.append(Spacer(1, 2*mm))
    story.append(_cargo_table(shipment, styles))
    story.append(Spacer(1, 2*mm))
    story.append(_bottom_block(shipment, styles))
    story.append(Spacer(1, 2*mm))
    story.append(_signature_block(styles))
    
    doc.build(story)
    return output_path
