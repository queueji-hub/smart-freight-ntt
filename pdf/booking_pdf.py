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
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

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
            fontName=THAI_FONT_BOLD, fontSize=18,
            textColor=BRAND_GOLD, alignment=TA_LEFT,
            spaceAfter=10, leading=22),
        "addr": ParagraphStyle("a", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, textColor=BRAND_BLUE,
            leading=13, spaceBefore=4),
        "title": ParagraphStyle("t", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=18, textColor=BRAND_BLUE,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=10),
        "label": ParagraphStyle("l", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=9),
        "value": ParagraphStyle("v", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9),
        "body": ParagraphStyle("b", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, leading=12),
        "footer": ParagraphStyle("f", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8,
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
        Spacer(1, 3*mm),
        Paragraph(addr, styles["addr"]),
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


def _clean_str(val, default="") -> str:
    if val is None:
        return default
    v = str(val).strip()
    return default if not v or v.lower() in ("none", "nan") else v


def _info_table(b, styles):
    """Two-column info table."""
    rev_no = b.get("revision_no")
    rev_str = f"REV {rev_no}" if rev_no is not None else "REV 0"

    gw = _clean_str(b.get("gross_weight"))
    cbm = _clean_str(b.get("measurement_cbm"))
    wt_cbm_str = f"{gw} KG / {cbm} CBM" if gw or cbm else "—"

    pkg_qty = _clean_str(b.get("package_qty"))
    pkg_unit = _clean_str(b.get("package_unit"), "PKGS")
    pkg_str = f"{pkg_qty} {pkg_unit}" if pkg_qty else "—"

    carrier = _clean_str(b.get("carrier"))
    liner = _clean_str(b.get("liner"))
    carrier_str = f"{carrier} / {liner}".strip(" /") if carrier or liner else "—"

    vessel = _clean_str(b.get("vessel"))
    voyage = _clean_str(b.get("voyage"))
    vessel_str = f"{vessel} {voyage}".strip() if vessel or voyage else "—"

    rows_left = [
        ("Booking No.", _clean_str(b.get("booking_no"))),
        ("Customer", _clean_str(b.get("customer_name"))),
        ("Shipper", _clean_str(b.get("shipper"))),
        ("Consignee", _clean_str(b.get("consignee"))),
        ("Notify Party", _clean_str(b.get("notify_party"))),
        ("Cargo Type", _clean_str(b.get("cargo_type"))),
        ("Commodity", _clean_str(b.get("commodity"))),
        ("Weight / CBM", wt_cbm_str),
        ("Packages", pkg_str),
    ]
    rows_right = [
        ("Revision No.", rev_str),
        ("Job Type", _clean_str(b.get("job_type"))),
        ("ETD", _fmt(b.get("etd")) or "—"),
        ("ETA", _fmt(b.get("eta")) or "—"),
        ("Carrier / Liner", carrier_str),
        ("Vessel / Voy", vessel_str),
        ("Containers", _clean_str(b.get("container_summary")) or "—"),
        ("Freight Term", _clean_str(b.get("freight_term")) or "—"),
        ("Closing Time", _clean_str(b.get("closing_time")) or "—"),
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
         Paragraph(_clean_str(b.get("pol")) or "—", styles["value"]),
         Paragraph("<b>POR (Port of Receipt)</b>", styles["label"]),
         Paragraph(_clean_str(b.get("por")) or "—", styles["value"])],
        [Paragraph("<b>POD (Port of Discharge)</b>", styles["label"]),
         Paragraph(_clean_str(b.get("pod")) or "—", styles["value"]),
         Paragraph("<b>Final Destination</b>", styles["label"]),
         Paragraph(_clean_str(b.get("final_destination")) or "—", styles["value"])],
        [Paragraph("<b>Transhipment Port</b>", styles["label"]),
         Paragraph(_clean_str(b.get("transhipment_port")) or "—", styles["value"]),
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
         Paragraph(_clean_str(b.get("cy_place")) or "—", styles["value"])],
        [Paragraph("<b>CFS Date</b>", styles["label"]),
         Paragraph(_fmt(b.get("cfs_date")) or "—", styles["value"]),
         Paragraph("<b>CFS Place</b>", styles["label"]),
         Paragraph(_clean_str(b.get("cfs_place")) or "—", styles["value"])],
        [Paragraph("<b>Customer Return Date</b>", styles["label"]),
         Paragraph(_fmt(b.get("customer_return_date")) or "—", styles["value"]),
         Paragraph("<b>Return Place</b>", styles["label"]),
         Paragraph(_clean_str(b.get("return_place")) or "—", styles["value"])],
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
    bno = booking.get("booking_no", "booking")
    rev = booking.get("revision_no", 0)
    
    if output_path is None:
        if rev and int(rev) > 0:
            output_path = str(Path(OUTPUT_DIR) / f"BC_{bno}_REV_{rev}.pdf")
        else:
            output_path = str(Path(OUTPUT_DIR) / f"BC_{bno}.pdf")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm,
        title=f"Booking Confirmation {bno}",
        author=COMPANY["name"],
    )
    styles = _styles()
    story = []
    
    story.append(_header(styles))
    story.append(Spacer(1, 4*mm))
    title_text = "BOOKING CONFIRMATION"
    if rev and int(rev) > 0:
        title_text += f" (REV {rev})"
    story.append(Paragraph(title_text, styles["title"]))
    story.append(_info_table(booking, styles))
    story.append(Spacer(1, 4*mm))
    story.append(_ports_table(booking, styles))
    story.append(Spacer(1, 4*mm))
    story.append(_dates_table(booking, styles))
    story.append(Spacer(1, 4*mm))
    
    remark_val = _clean_str(booking.get("remark"))
    if remark_val:
        story.append(Paragraph("<b>Remark / Special Instructions:</b>",
                                styles["label"]))
        story.append(Paragraph(remark_val.replace("\n", "<br/>"),
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
    canvas.setFont(THAI_FONT, 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 10*mm, f"Page {doc.page}")
    canvas.restoreState()
