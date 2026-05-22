"""A4 Booking Confirmation PDF generator."""
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

BRAND_BLUE = colors.HexColor("#1F4E9E")
BRAND_GOLD = colors.HexColor("#C9A227")
HEADER_GREY = colors.HexColor("#9CA3AF")


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
        "company": ParagraphStyle("c", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=16,
            textColor=BRAND_GOLD, alignment=TA_LEFT),
        "addr": ParagraphStyle("a", parent=base["Normal"],
            fontName="Helvetica", fontSize=9, textColor=BRAND_BLUE, leading=12),
        "title": ParagraphStyle("t", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=18, textColor=BRAND_BLUE,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=10),
        "label": ParagraphStyle("l", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9),
        "value": ParagraphStyle("v", parent=base["Normal"],
            fontName="Helvetica", fontSize=9),
        "body": ParagraphStyle("b", parent=base["Normal"],
            fontName="Helvetica", fontSize=9, leading=12),
        "footer": ParagraphStyle("f", parent=base["Normal"],
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=colors.grey, alignment=TA_CENTER),
    }


def _header(styles):
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(logo_path)
        iw, ih = ir.getSize()
        scale = min(45*mm / iw, 28*mm / ih)
        logo = Image(logo_path, width=iw*scale, height=ih*scale)
    else:
        logo = Paragraph("[LOGO]", styles["body"])
    
    addr = (f'<font color="#1F4E9E" size="9">'
            f'{COMPANY["address_line1"]}<br/>'
            f'{COMPANY["address_line2"]}<br/>'
            f'{COMPANY["address_line3"]} Tax ID {COMPANY["tax_id"]}<br/>'
            f'Tel {COMPANY["tel"]} · Email: {COMPANY["email"]}'
            f'</font>')
    
    company_block = [
        Paragraph(COMPANY["name"], styles["company"]),
        Paragraph(addr, styles["addr"]),
    ]
    
    tbl = Table([[logo, company_block]], colWidths=[45*mm, 135*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    return tbl


def _info_table(b, styles):
    """Two-column info table."""
    rows_left = [
        ("Booking No.", b.get("booking_no", "")),
        ("Customer", b.get("customer_name", "")),
        ("Shipper", b.get("shipper", "")),
        ("Consignee", b.get("consignee", "")),
        ("Notify Party", b.get("notify_party", "")),
        ("Cargo Type", b.get("cargo_type", "")),
        ("Commodity", b.get("commodity", "")),
        ("Quantity", b.get("quantity", "")),
    ]
    rows_right = [
        ("Job Type", b.get("job_type", "")),
        ("ETD", _fmt(b.get("etd"))),
        ("ETA", _fmt(b.get("eta"))),
        ("Carrier", b.get("carrier", "")),
        ("M.Vessel", b.get("m_vessel", "")),
        ("Feeder", b.get("feeder", "")),
        ("Liner", b.get("liner", "")),
        ("Closing Time", b.get("closing_time", "")),
    ]
    
    data = []
    for (ll, lv), (rl, rv) in zip(rows_left, rows_right):
        data.append([
            Paragraph(f"<b>{ll}</b>", styles["label"]),
            Paragraph(f": {lv}", styles["value"]),
            Paragraph(f"<b>{rl}</b>", styles["label"]),
            Paragraph(f": {rv}", styles["value"]),
        ])
    
    tbl = Table(data, colWidths=[28*mm, 62*mm, 28*mm, 62*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LINEABOVE", (0,0), (-1,0), 1, colors.black),
        ("LINEBELOW", (0,-1), (-1,-1), 1, colors.black),
    ]))
    return tbl


def _ports_table(b, styles):
    """Routing ports table."""
    data = [
        [Paragraph("<b>Routing</b>", styles["label"]), "", "", ""],
        [Paragraph("<b>POL (Port of Loading)</b>", styles["label"]),
         Paragraph(b.get("pol", "") or "—", styles["value"]),
         Paragraph("<b>POR (Port of Receipt)</b>", styles["label"]),
         Paragraph(b.get("por", "") or "—", styles["value"])],
        [Paragraph("<b>POD (Port of Discharge)</b>", styles["label"]),
         Paragraph(b.get("pod", "") or "—", styles["value"]),
         Paragraph("<b>Final Destination</b>", styles["label"]),
         Paragraph(b.get("final_destination", "") or "—", styles["value"])],
        [Paragraph("<b>Transhipment Port</b>", styles["label"]),
         Paragraph(b.get("transhipment_port", "") or "—", styles["value"]),
         "", ""],
    ]
    tbl = Table(data, colWidths=[40*mm, 50*mm, 40*mm, 50*mm])
    tbl.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), BRAND_BLUE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.grey),
    ]))
    return tbl


def _dates_table(b, styles):
    """CY/CFS/Return dates table."""
    data = [
        [Paragraph("<b>Container Yard / CFS Schedule</b>", styles["label"]),
         "", "", ""],
        [Paragraph("<b>CY Date</b>", styles["label"]),
         Paragraph(_fmt(b.get("cy_date")) or "—", styles["value"]),
         Paragraph("<b>CY Place</b>", styles["label"]),
         Paragraph(b.get("cy_place", "") or "—", styles["value"])],
        [Paragraph("<b>CFS Date</b>", styles["label"]),
         Paragraph(_fmt(b.get("cfs_date")) or "—", styles["value"]),
         Paragraph("<b>CFS Place</b>", styles["label"]),
         Paragraph(b.get("cfs_place", "") or "—", styles["value"])],
        [Paragraph("<b>Customer Return Date</b>", styles["label"]),
         Paragraph(_fmt(b.get("customer_return_date")) or "—", styles["value"]),
         Paragraph("<b>Return Place</b>", styles["label"]),
         Paragraph(b.get("return_place", "") or "—", styles["value"])],
    ]
    tbl = Table(data, colWidths=[40*mm, 50*mm, 40*mm, 50*mm])
    tbl.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), BRAND_GOLD),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.grey),
    ]))
    return tbl


def generate_booking_pdf(booking: Dict[str, Any], output_path: str = None) -> str:
    """Generate Booking Confirmation PDF."""
    if output_path is None:
        bno = booking.get("booking_no", "booking")
        output_path = str(Path(OUTPUT_DIR) / f"BC_{bno}.pdf")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm,
        title=f"Booking Confirmation {booking.get('booking_no','')}",
        author=COMPANY["name"],
    )
    styles = _styles()
    story = []
    
    story.append(_header(styles))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("BOOKING CONFIRMATION", styles["title"]))
    story.append(_info_table(booking, styles))
    story.append(Spacer(1, 4*mm))
    story.append(_ports_table(booking, styles))
    story.append(Spacer(1, 4*mm))
    story.append(_dates_table(booking, styles))
    story.append(Spacer(1, 4*mm))
    
    if booking.get("remark"):
        story.append(Paragraph("<b>Remark / Special Instructions:</b>",
                                styles["label"]))
        story.append(Paragraph(booking.get("remark", "").replace("\n", "<br/>"),
                                styles["body"]))
        story.append(Spacer(1, 4*mm))
    
    # Signature
    sig_data = [[
        [Paragraph("Yours sincerely,", styles["body"]),
         Spacer(1, 18*mm),
         Paragraph("_" * 30, styles["body"]),
         Paragraph(f"<b>{COMPANY['signer_name']}</b>", styles["body"]),
         Paragraph(COMPANY["signer_title"], styles["body"])],
        [Spacer(1, 18*mm + 12),
         Paragraph("_" * 30, styles["body"]),
         Paragraph("Authorized Signature", styles["body"])],
    ]]
    sig = Table(sig_data, colWidths=[90*mm, 90*mm])
    sig.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(Spacer(1, 8*mm))
    story.append(sig)
    
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output_path


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 10*mm, f"Page {doc.page}")
    canvas.restoreState()
