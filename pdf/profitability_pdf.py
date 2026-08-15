"""Job Profitability PDF — production reporting output for Job 360."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import register_thai_fonts

THAI_FONT, THAI_FONT_BOLD = register_thai_fonts()
NAVY = colors.HexColor("#0F172A")
BLUE = colors.HexColor("#1F4E9E")
BORDER = colors.HexColor("#D1D5DB")
LIGHT = colors.HexColor("#F8FAFC")
TEXT = colors.HexColor("#1E293B")
GREEN = colors.HexColor("#166534")
RED = colors.HexColor("#991B1B")


def _s(value: Any, default: str = "-") -> str:
    text = str(value or "").strip()
    return default if not text or text.lower() in {"none", "nan", "nat"} else text


def _money(value: Any, currency: str = "THB") -> str:
    try:
        return f"{float(value or 0):,.2f} {currency}"
    except (TypeError, ValueError):
        return f"0.00 {currency}"


def generate_profitability_pdf(job: Dict[str, Any], profit: Dict[str, Any], output_path: str | None = None) -> str:
    job_no = _s(job.get("job_no"), "JOB")
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"Profitability_{job_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=f"Job Profitability {job_no}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Normal"], fontName=THAI_FONT_BOLD, fontSize=17, textColor=NAVY, leading=20)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontName=THAI_FONT, fontSize=8.5, textColor=TEXT, leading=11)
    head = ParagraphStyle("head", parent=styles["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, textColor=colors.white, leading=11)
    label = ParagraphStyle("label", parent=styles["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, textColor=NAVY, leading=11)
    value = ParagraphStyle("value", parent=styles["Normal"], fontName=THAI_FONT, fontSize=8.5, textColor=TEXT, leading=11)
    right = ParagraphStyle("right", parent=value, alignment=TA_RIGHT)

    total_revenue = float(profit.get("ar_actual", 0) or 0)
    total_cost = float(profit.get("ap_accrued", 0) or 0) + float(profit.get("ap_actual", 0) or 0) + float(profit.get("ap_posted", 0) or 0)
    profit_value = float(profit.get("actual_net_profit", 0) or 0)
    margin = (profit_value / total_revenue * 100.0) if total_revenue else 0.0
    accent = GREEN if profit_value >= 0 else RED

    story = [
        Paragraph(COMPANY.get("name", "NATTAYARAAT CO., LTD."), title),
        Paragraph(f"{_s(COMPANY.get('address_line1'), '')} · Tax ID {_s(COMPANY.get('tax_id'), '')}", sub),
        Spacer(1, 3 * mm),
        Paragraph("JOB PROFITABILITY", title),
        Spacer(1, 3 * mm),
    ]

    info = Table([
        [Paragraph("Job No.", label), Paragraph(job_no, value), Paragraph("Customer", label), Paragraph(_s(job.get("customer_name")), value)],
        [Paragraph("Mode", label), Paragraph(_s(job.get("mode") or job.get("job_type")), value), Paragraph("POL / POD", label), Paragraph(f"{_s(job.get('pol'))} / {_s(job.get('pod'))}", value)],
        [Paragraph("ETD / ETA", label), Paragraph(f"{_s(job.get('etd'))} / {_s(job.get('eta'))}", value), Paragraph("Status", label), Paragraph(_s(job.get("status")), value)],
    ], colWidths=[24*mm, 60*mm, 25*mm, 71*mm])
    info.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.3, BORDER),
        ("BACKGROUND", (0,0), (-1,-1), LIGHT),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.extend([info, Spacer(1, 5 * mm)])

    summary = Table([
        [Paragraph("Revenue", head), Paragraph("Cost", head), Paragraph("Gross Profit", head), Paragraph("Margin", head)],
        [Paragraph(_money(total_revenue), right), Paragraph(_money(total_cost), right), Paragraph(_money(profit_value), right), Paragraph(f"{margin:,.2f}%", right)],
    ], colWidths=[45*mm]*4)
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE),
        ("BACKGROUND", (0,1), (-1,1), colors.white),
        ("TEXTCOLOR", (2,1), (2,1), accent),
        ("BOX", (0,0), (-1,-1), 0.6, BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.3, BORDER),
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.extend([summary, Spacer(1, 6 * mm)])

    detail_rows = [
        [Paragraph("Revenue", head), Paragraph(_money(profit.get("ar_estimated")), right), Paragraph(_money(profit.get("ar_actual")), right)],
        [Paragraph("AP Estimated", value), Paragraph(_money(profit.get("ap_estimated")), right), Paragraph("", value)],
        [Paragraph("AP Accrued", value), Paragraph(_money(profit.get("ap_accrued")), right), Paragraph("", value)],
        [Paragraph("AP Actual", value), Paragraph(_money(profit.get("ap_actual")), right), Paragraph("", value)],
        [Paragraph("AP Posted", value), Paragraph(_money(profit.get("ap_posted")), right), Paragraph("", value)],
    ]
    detail = Table(detail_rows, colWidths=[80*mm, 55*mm, 55*mm])
    detail.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.3, BORDER),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(detail)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Prepared for internal operational and financial review.", sub))

    doc.build(story)
    return output_path
