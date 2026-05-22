"""Job Profitability & Approval Sheet PDF generator."""
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

BRAND_BLUE = colors.HexColor("#1F4E9E")
BRAND_GOLD = colors.HexColor("#C9A227")
PROFIT_GREEN = colors.HexColor("#26B574")
LOSS_RED = colors.HexColor("#E5484D")
HEADER_GREY = colors.HexColor("#9CA3AF")


def _money(n) -> str:
    try:
        return f"{float(n or 0):,.2f}"
    except Exception:
        return "0.00"


def _styles():
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle("c", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=16, textColor=BRAND_GOLD,
            spaceAfter=8, leading=20),
        "addr": ParagraphStyle("a", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8, textColor=BRAND_BLUE,
            leading=11, spaceBefore=3),
        "title": ParagraphStyle("t", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=18, textColor=BRAND_BLUE,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=8),
        "subtitle": ParagraphStyle("st", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, textColor=colors.grey,
            alignment=TA_CENTER, spaceAfter=8),
        "label": ParagraphStyle("l", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8),
        "value": ParagraphStyle("v", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8, leading=10),
        "right": ParagraphStyle("r", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8, alignment=TA_RIGHT),
        "right_b": ParagraphStyle("rb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=9, alignment=TA_RIGHT),
        "body": ParagraphStyle("b", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8, leading=10),
        "small": ParagraphStyle("s", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=7, leading=9),
    }


def _header(styles):
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(logo_path)
        iw, ih = ir.getSize()
        scale = min(35*mm / iw, 22*mm / ih)
        logo = Image(logo_path, width=iw*scale, height=ih*scale)
    else:
        logo = Paragraph("[LOGO]", styles["body"])
    
    addr = (f'<font color="#1F4E9E" size="8">'
            f'{COMPANY["address_line1"]}<br/>'
            f'{COMPANY["address_line2"]} {COMPANY["address_line3"]}<br/>'
            f'Tax ID: {COMPANY["tax_id"]} · Tel: {COMPANY["tel"]}'
            f'</font>')
    
    company_block = [
        Paragraph(COMPANY["name"], styles["company"]),
        Spacer(1, 2.5*mm),
        Paragraph(addr, styles["addr"]),
    ]
    
    tbl = Table([[logo, company_block]], colWidths=[35*mm, 145*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return tbl


def _job_info_table(shipment, sheet, styles):
    rows = [
        [Paragraph("<b>Sheet No.</b>", styles["label"]),
         Paragraph(sheet.get("sheet_no", ""), styles["value"]),
         Paragraph("<b>Job No.</b>", styles["label"]),
         Paragraph(shipment.get("job_no", ""), styles["value"])],
        [Paragraph("<b>Customer</b>", styles["label"]),
         Paragraph(shipment.get("customer_name", "—"), styles["value"]),
         Paragraph("<b>Job Type</b>", styles["label"]),
         Paragraph(shipment.get("job_type", "—"), styles["value"])],
        [Paragraph("<b>Carrier</b>", styles["label"]),
         Paragraph(shipment.get("carrier", "—"), styles["value"]),
         Paragraph("<b>Vessel</b>", styles["label"]),
         Paragraph(shipment.get("m_vessel", "—"), styles["value"])],
        [Paragraph("<b>POL</b>", styles["label"]),
         Paragraph(shipment.get("pol", "—"), styles["value"]),
         Paragraph("<b>POD</b>", styles["label"]),
         Paragraph(shipment.get("pod", "—"), styles["value"])],
        [Paragraph("<b>Container</b>", styles["label"]),
         Paragraph(shipment.get("container_no", "—"), styles["value"]),
         Paragraph("<b>Size</b>", styles["label"]),
         Paragraph(shipment.get("container_size", "—"), styles["value"])],
        [Paragraph("<b>ETD</b>", styles["label"]),
         Paragraph(shipment.get("etd", "—") or "—", styles["value"]),
         Paragraph("<b>ETA</b>", styles["label"]),
         Paragraph(shipment.get("eta", "—") or "—", styles["value"])],
    ]
    tbl = Table(rows, colWidths=[28*mm, 62*mm, 28*mm, 62*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.grey),
    ]))
    return tbl


def _cost_table(title: str, lines: List[Dict[str, Any]],
                 color, styles, total_label: str):
    """Generic cost table for AR or AP."""
    header = [
        Paragraph(f'<font color="white"><b>{title}</b></font>',
                   styles["label"]),
        "", "", "", "", "",
    ]
    sub_header = [
        Paragraph("<b>#</b>", styles["label"]),
        Paragraph("<b>Category</b>", styles["label"]),
        Paragraph("<b>Description</b>", styles["label"]),
        Paragraph("<b>Supplier</b>", styles["label"]),
        Paragraph("<b>Currency</b>", styles["label"]),
        Paragraph("<b>Amount (THB)</b>", styles["label"]),
    ]
    
    data = [header, sub_header]
    total = 0
    
    if not lines:
        data.append([Paragraph("—", styles["small"])] * 6)
    else:
        for i, line in enumerate(lines, 1):
            amount_thb = line.get("amount_thb") or line.get("amount", 0) or 0
            total += amount_thb
            cur_amt = (f"{line.get('currency','THB')} "
                       f"{_money(line.get('amount', 0))}")
            data.append([
                Paragraph(str(i), styles["small"]),
                Paragraph(line.get("category") or "—", styles["small"]),
                Paragraph(line.get("description") or "—", styles["small"]),
                Paragraph(line.get("supplier") or "—", styles["small"]),
                Paragraph(cur_amt, styles["small"]),
                Paragraph(_money(amount_thb), styles["right"]),
            ])
    
    # Total row
    data.append([
        "", "", "", "",
        Paragraph(f"<b>{total_label}</b>", styles["label"]),
        Paragraph(f"<b>{_money(total)}</b>", styles["right_b"]),
    ])
    
    tbl = Table(data, colWidths=[8*mm, 32*mm, 50*mm, 35*mm, 25*mm, 30*mm])
    tbl.setStyle(TableStyle([
        # Title row spans full width
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), color),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        # Sub-header
        ("BACKGROUND", (0,1), (-1,1), HEADER_GREY),
        ("ALIGN", (0,1), (-1,1), "CENTER"),
        # Body
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        # Total row
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#E5E7EB")),
        ("LINEABOVE", (0,-1), (-1,-1), 1, colors.black),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("INNERGRID", (0,1), (-1,-2), 0.3, colors.grey),
    ]))
    return tbl


def _summary_box(summary: Dict[str, Any], styles):
    """Profit summary highlighted box."""
    margin = summary.get("profit_margin", 0)
    is_profit = (summary.get("net_profit", 0) >= 0)
    color = PROFIT_GREEN if is_profit else LOSS_RED
    
    rows = [
        [Paragraph("<b>FINANCIAL SUMMARY</b>", styles["label"]), ""],
        [Paragraph("Total Revenue (AR)", styles["body"]),
         Paragraph(f"THB {_money(summary['total_ar'])}", styles["right"])],
        [Paragraph("Total Cost (AP)", styles["body"]),
         Paragraph(f"THB {_money(summary['total_ap'])}", styles["right"])],
        [Paragraph(f'<b><font color="{color.hexval()}">Net Profit</font></b>',
                    styles["label"]),
         Paragraph(f'<b><font color="{color.hexval()}">'
                    f'THB {_money(summary["net_profit"])}</font></b>',
                    styles["right_b"])],
        [Paragraph(f'<b><font color="{color.hexval()}">Profit Margin</font></b>',
                    styles["label"]),
         Paragraph(f'<b><font color="{color.hexval()}">'
                    f'{margin:.2f}%</font></b>', styles["right_b"])],
    ]
    
    tbl = Table(rows, colWidths=[100*mm, 80*mm])
    tbl.setStyle(TableStyle([
        ("SPAN", (0,0), (-1,0)),
        ("BACKGROUND", (0,0), (-1,0), BRAND_BLUE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("INNERGRID", (0,1), (-1,-1), 0.3, colors.grey),
        ("LINEABOVE", (0,3), (-1,3), 1.5, colors.black),
    ]))
    return tbl


def _signature_block(sheet, styles):
    """Three-column signature block."""
    cells = []
    for role, name_field, date_field, label in [
        ("Prepared By (CS / Operation)",
         "prepared_by", "prepared_at", "Date prepared"),
        ("Reviewed By (Sales)",
         "reviewed_by", "reviewed_at", "Date reviewed"),
        ("Approved By (Management)",
         "approved_by", "approved_at", "Date approved"),
    ]:
        name = sheet.get(name_field) or ""
        date_val = sheet.get(date_field) or ""
        if date_val:
            date_val = date_val[:10]
        
        cell = [
            Paragraph(f"<b>{role}</b>", styles["label"]),
            Spacer(1, 16*mm),
            Paragraph("_" * 28, styles["body"]),
            Paragraph(f"Name: <b>{name or '_____________'}</b>",
                      styles["body"]),
            Paragraph(f"Date: <b>{date_val or '_____________'}</b>",
                      styles["body"]),
        ]
        cells.append(cell)
    
    tbl = Table([cells], colWidths=[60*mm, 60*mm, 60*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("LINEAFTER", (0,0), (1,0), 0.5, colors.grey),
    ]))
    return tbl


def generate_profit_pdf(shipment: Dict[str, Any],
                          ar_lines: List[Dict[str, Any]],
                          ap_lines: List[Dict[str, Any]],
                          summary: Dict[str, Any],
                          sheet: Dict[str, Any],
                          output_path: str = None) -> str:
    """Generate Profit Sheet PDF with sign-off lines."""
    if output_path is None:
        sheet_no = sheet.get("sheet_no", "PS")
        output_path = str(Path(OUTPUT_DIR) / f"{sheet_no}.pdf")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=12*mm, bottomMargin=15*mm,
        title=f"Profit Sheet {sheet.get('sheet_no','')}",
        author=COMPANY["name"],
    )
    styles = _styles()
    story = []
    
    story.append(_header(styles))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("JOB PROFITABILITY & APPROVAL SHEET", styles["title"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}",
        styles["subtitle"]))
    
    story.append(_job_info_table(shipment, sheet, styles))
    story.append(Spacer(1, 4*mm))
    
    # AR (Revenue)
    story.append(_cost_table(
        "ACCOUNT RECEIVABLES (AR) — REVENUE / SELLING",
        ar_lines, PROFIT_GREEN, styles, "TOTAL REVENUE"
    ))
    story.append(Spacer(1, 3*mm))
    
    # AP (Cost)
    story.append(_cost_table(
        "ACCOUNT PAYABLES (AP) — COST / SUPPLIER",
        ap_lines, LOSS_RED, styles, "TOTAL COST"
    ))
    story.append(Spacer(1, 5*mm))
    
    # Summary
    summary_wrap = Table([["", _summary_box(summary, styles)]],
                          colWidths=[0*mm, 180*mm])
    summary_wrap.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(summary_wrap)
    story.append(Spacer(1, 6*mm))
    
    # Sign-off
    story.append(Paragraph("<b>Sign-off:</b>", styles["label"]))
    story.append(Spacer(1, 2*mm))
    story.append(_signature_block(sheet, styles))
    
    doc.build(story)
    return output_path
