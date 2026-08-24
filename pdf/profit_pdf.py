"""Job Profitability & Operation Sheet PDF Generator.

Enterprise Freight Forwarding Standard:
- Complete Master Operational Data: Job No, Carrier, Carrier MBL, Booking No, HBL, Quotation No
- Commercial & Routing Context: Shipper, Consignee, Notify, POL, POD, Transshipment, Vessel, Mother Vessel, ETD, ETA
- Cargo & Container Manifest: Commodity, Weights (Gross/Net/Chargeable), CBM, Packages, Container & Seal Nos
- Full Itemized AR (Revenue/Selling) and AP (Cost/Supplier) Financial Tables
- Performance KPI Summary (Total Revenue, Total Cost, Net Profit, Profit Margin %)
- Dual / Triple Formal Sign-off Blocks (Operations, Accounting, Management Approval)
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.utils import ImageReader

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

BRAND_NAVY = colors.HexColor("#0F294A")
BRAND_BLUE = colors.HexColor("#1D4ED8")
BLUE_LIGHT = colors.HexColor("#EFF6FF")
PROFIT_GREEN = colors.HexColor("#15803D")
PROFIT_BG = colors.HexColor("#F0FDF4")
LOSS_RED = colors.HexColor("#B91C1C")
LOSS_BG = colors.HexColor("#FEF2F2")
BORDER_COLOR = colors.HexColor("#94A3B8")
TABLE_HEADER_BG = colors.HexColor("#1E293B")
SUB_HEADER_BG = colors.HexColor("#F1F5F9")
TEXT_DARK = colors.HexColor("#0F172A")


def _s(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if not text or text.lower() in {"none", "nan", "nat"} else text


def _money(n) -> str:
    try:
        return f"{float(n or 0):,.2f}"
    except Exception:
        return "0.00"


def _styles():
    base = getSampleStyleSheet()
    return {
        "company_th": ParagraphStyle("p_comp_th", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=10, leading=12.5, textColor=BRAND_NAVY),
        "company_en": ParagraphStyle("p_comp_en", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=11, textColor=BRAND_NAVY),
        "company_addr": ParagraphStyle("p_comp_addr", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.0, leading=9.2, textColor=TEXT_DARK),
        
        "title": ParagraphStyle("p_title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=13.0, leading=15, textColor=BRAND_NAVY, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("p_subtitle", parent=base["Normal"], fontName=THAI_FONT, fontSize=8.0, leading=10, textColor=colors.HexColor("#475569"), alignment=TA_CENTER),
        
        "sec_title": ParagraphStyle("p_sec_title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.0, leading=10, textColor=colors.white),
        "th_center": ParagraphStyle("p_th_center", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "th_left": ParagraphStyle("p_th_left", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_LEFT, textColor=TEXT_DARK),
        "th_right": ParagraphStyle("p_th_right", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "label": ParagraphStyle("p_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, textColor=TEXT_DARK),
        "value": ParagraphStyle("p_value", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, textColor=TEXT_DARK),
        "value_b": ParagraphStyle("p_value_b", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, textColor=TEXT_DARK),
        
        "td_center": ParagraphStyle("p_td_center", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_CENTER, textColor=TEXT_DARK),
        "td_left": ParagraphStyle("p_td_left", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_LEFT, textColor=TEXT_DARK),
        "td_right": ParagraphStyle("p_td_right", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "td_right_b": ParagraphStyle("p_td_right_b", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "sign_role": ParagraphStyle("p_sign_role", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.0, alignment=TA_CENTER, textColor=TEXT_DARK),
        "sign_name": ParagraphStyle("p_sign_name", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=TEXT_DARK),
    }


def _header(styles) -> Table:
    logo_path = COMPANY.get("logo_path")
    logo = None
    if logo_path and Path(str(logo_path)).exists():
        try:
            ir = ImageReader(str(logo_path))
            iw, ih = ir.getSize()
            scale = min(32 * mm / iw, 17 * mm / ih)
            logo = Image(str(logo_path), width=iw * scale, height=ih * scale)
        except Exception:
            logo = None
    if logo is None:
        logo = Paragraph("<b>NATTAYAARAT</b>", styles["company_th"])

    comp_th = "บริษัท ณัฐยาราชย์ จำกัด (สำนักงานใหญ่)"
    comp_en = "NATTAYAARAT CO.,LTD. (Head Office)"
    addr_line = "เลขที่ 59/9 หมู่ที่ 4 ตำบลบางกระทึก อำเภอสามพราน จังหวัดนครปฐม 73210"
    tax_tel = f"เลขประจำตัวผู้เสียภาษี: {COMPANY.get('tax_id', '0735568004823')} | โทร: {COMPANY.get('tel', '')}"

    comp_block = [
        Paragraph(f"<b>{comp_th}</b>", styles["company_th"]),
        Paragraph(f"<b>{comp_en}</b>", styles["company_en"]),
        Paragraph(addr_line, styles["company_addr"]),
        Paragraph(tax_tel, styles["company_addr"]),
    ]

    tbl = Table([[logo, comp_block]], colWidths=[36 * mm, 148 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 4),
    ]))
    return tbl


def _job_info_grid(shipment: Dict[str, Any], sheet: Dict[str, Any], styles) -> Table:
    vessel_str = f"{_s(shipment.get('vessel'))} {_s(shipment.get('voyage'))}".strip()
    mv_str = f"{_s(shipment.get('mother_vessel'))} {_s(shipment.get('mother_voyage'))}".strip()
    
    rows = [
        [
            Paragraph("<b>Job No.</b>", styles["label"]),
            Paragraph(f"<b>{_s(shipment.get('job_no'))}</b>", styles["value_b"]),
            Paragraph("<b>Sheet No.</b>", styles["label"]),
            Paragraph(_s(sheet.get("sheet_no") or shipment.get("profit_sheet_no")), styles["value"]),
            Paragraph("<b>Status</b>", styles["label"]),
            Paragraph(_s(shipment.get("status") or "Proceed"), styles["value"]),
        ],
        [
            Paragraph("<b>Customer</b>", styles["label"]),
            Paragraph(_s(shipment.get("customer_name") or shipment.get("customer")), styles["value"]),
            Paragraph("<b>Carrier</b>", styles["label"]),
            Paragraph(_s(shipment.get("carrier")), styles["value"]),
            Paragraph("<b>Booking No.</b>", styles["label"]),
            Paragraph(_s(shipment.get("booking_no")), styles["value"]),
        ],
        [
            Paragraph("<b>Shipper</b>", styles["label"]),
            Paragraph(_s(shipment.get("shipper")), styles["value"]),
            Paragraph("<b>Carrier MBL</b>", styles["label"]),
            Paragraph(f"<b>{_s(shipment.get('mbl_no'))}</b>", styles["value_b"]),
            Paragraph("<b>Company HBL</b>", styles["label"]),
            Paragraph(_s(shipment.get("hbl_no") or shipment.get("bl_no")), styles["value"]),
        ],
        [
            Paragraph("<b>Consignee</b>", styles["label"]),
            Paragraph(_s(shipment.get("consignee")), styles["value"]),
            Paragraph("<b>Vessel / Voy</b>", styles["label"]),
            Paragraph(vessel_str if vessel_str != "—" else "—", styles["value"]),
            Paragraph("<b>Mother Vessel</b>", styles["label"]),
            Paragraph(mv_str if mv_str != "—" else "—", styles["value"]),
        ],
        [
            Paragraph("<b>POL / POD</b>", styles["label"]),
            Paragraph(f"{_s(shipment.get('pol'))} → {_s(shipment.get('pod'))}", styles["value"]),
            Paragraph("<b>ETD / ETA</b>", styles["label"]),
            Paragraph(f"{_s(shipment.get('etd'))} / {_s(shipment.get('eta'))}", styles["value"]),
            Paragraph("<b>Incoterms / Svc</b>", styles["label"]),
            Paragraph(f"{_s(shipment.get('incoterm'))} · {_s(shipment.get('service_type'))}", styles["value"]),
        ],
        [
            Paragraph("<b>Commodity</b>", styles["label"]),
            Paragraph(_s(shipment.get("commodity")), styles["value"]),
            Paragraph("<b>Gross Wt / CBM</b>", styles["label"]),
            Paragraph(f"{_s(shipment.get('gross_weight'))} KGS / {_s(shipment.get('cbm'))} CBM", styles["value"]),
            Paragraph("<b>Sales / Ops</b>", styles["label"]),
            Paragraph(f"{_s(shipment.get('sales_person'))} / {_s(shipment.get('operations_owner') or shipment.get('created_by'))}", styles["value"]),
        ],
    ]

    tbl = Table(rows, colWidths=[24 * mm, 46 * mm, 24 * mm, 42 * mm, 22 * mm, 26 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, BRAND_BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
    ]))
    return tbl


def _cost_table(title: str, lines: List[Dict[str, Any]], bg_color, styles, total_label: str, is_ar: bool = True) -> Table:
    header = [
        Paragraph(f"<b>{title}</b>", styles["sec_title"]),
        "", "", "", "", "",
    ]
    sub_header = [
        Paragraph("<b>#</b>", styles["th_center"]),
        Paragraph("<b>Category</b>", styles["th_left"]),
        Paragraph("<b>Description</b>", styles["th_left"]),
        Paragraph("<b>Party / Vendor</b>" if not is_ar else "<b>Payer / Customer</b>", styles["th_left"]),
        Paragraph("<b>Currency & Amt</b>", styles["th_right"]),
        Paragraph("<b>Amount (THB)</b>", styles["th_right"]),
    ]

    data = [header, sub_header]
    total_thb = 0.0

    if not lines:
        data.append([Paragraph("—", styles["td_center"])] * 6)
    else:
        for i, line in enumerate(lines, 1):
            amt_thb = float(line.get("amount_thb") or line.get("amount", 0) or 0)
            total_thb += amt_thb
            curr = str(line.get("currency") or "THB").upper()
            orig_amt = float(line.get("amount") or amt_thb)
            curr_str = f"{curr} {orig_amt:,.2f}" if curr != "THB" else f"{orig_amt:,.2f}"
            party = _s(line.get("supplier") or line.get("vendor_name") or line.get("customer"))
            ref_no = line.get("vendor_invoice_no") if not is_ar else line.get("invoice_no")
            if ref_no and str(ref_no).strip() not in ("—", "None", ""):
                party_cell = f"{party}<br/><font color='#64748B' size='6'>Ref: {ref_no}</font>"
            else:
                party_cell = party

            data.append([
                Paragraph(str(i), styles["td_center"]),
                Paragraph(_s(line.get("category")), styles["td_left"]),
                Paragraph(_s(line.get("description")), styles["td_left"]),
                Paragraph(party_cell, styles["td_left"]),
                Paragraph(curr_str, styles["td_right"]),
                Paragraph(f"{amt_thb:,.2f}", styles["td_right"]),
            ])

    data.append([
        "", "", "", "",
        Paragraph(f"<b>{total_label}</b>", styles["td_right_b"]),
        Paragraph(f"<b>{total_thb:,.2f}</b>", styles["td_right_b"]),
    ])

    tbl = Table(data, colWidths=[8 * mm, 28 * mm, 54 * mm, 42 * mm, 26 * mm, 26 * mm])
    tbl.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), bg_color),
        ("BACKGROUND", (0, 1), (-1, 1), SUB_HEADER_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F8FAFC")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, TEXT_DARK),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_COLOR),
        ("INNERGRID", (0, 1), (-1, -2), 0.25, colors.HexColor("#E2E8F0")),
    ]))
    return tbl


def _summary_card(summary: Dict[str, Any], ar_total: float, ap_total: float, styles) -> Table:
    rev = float(summary.get("total_ar") or summary.get("ar_actual") or ar_total or 0)
    cost = float(summary.get("total_ap") or summary.get("ap_actual") or ap_total or 0)
    profit = float(summary.get("net_profit") or summary.get("actual_net_profit") or (rev - cost))
    margin = float(summary.get("profit_margin") or summary.get("actual_margin_pct") or ((profit / rev * 100) if rev > 0 else 0))
    
    is_profit = (profit >= 0)
    p_color = PROFIT_GREEN if is_profit else LOSS_RED
    p_bg = PROFIT_BG if is_profit else LOSS_BG

    rows = [
        [
            Paragraph("<b>TOTAL REVENUE (AR)</b>", styles["th_center"]),
            Paragraph("<b>TOTAL COST (AP)</b>", styles["th_center"]),
            Paragraph("<b>GROSS / NET PROFIT</b>", styles["th_center"]),
            Paragraph("<b>PROFIT MARGIN</b>", styles["th_center"]),
        ],
        [
            Paragraph(f"<b>THB {rev:,.2f}</b>", styles["th_center"]),
            Paragraph(f"<b>THB {cost:,.2f}</b>", styles["th_center"]),
            Paragraph(f"<font color='{p_color.hexval()}'><b>THB {profit:,.2f}</b></font>", styles["th_center"]),
            Paragraph(f"<font color='{p_color.hexval()}'><b>{margin:.2f}%</b></font>", styles["th_center"]),
        ]
    ]

    tbl = Table(rows, colWidths=[46 * mm, 46 * mm, 46 * mm, 46 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SUB_HEADER_BG),
        ("BACKGROUND", (0, 1), (1, 1), colors.white),
        ("BACKGROUND", (2, 1), (3, 1), p_bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("BOX", (0, 0), (-1, -1), 0.8, BRAND_NAVY),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
    ]))
    return tbl


def _signature_block(styles) -> Table:
    box1 = [
        Paragraph("<b>ผู้จัดทำ (Operations)</b>", styles["sign_role"]),
        Paragraph("Prepared By", styles["sign_name"]),
        Spacer(1, 12 * mm),
        Paragraph("วันที่/Date: _____/____/________", styles["sign_name"]),
    ]

    box2 = [
        Paragraph("<b>ผู้ตรวจสอบ (Accounting)</b>", styles["sign_role"]),
        Paragraph("Verified By", styles["sign_name"]),
        Spacer(1, 12 * mm),
        Paragraph("วันที่/Date: _____/____/________", styles["sign_name"]),
    ]

    box3 = [
        Paragraph("<b>ผู้อนุมัติ (Management)</b>", styles["sign_role"]),
        Paragraph("Authorized Approval", styles["sign_name"]),
        Spacer(1, 12 * mm),
        Paragraph("วันที่/Date: _____/____/________", styles["sign_name"]),
    ]

    sig_tbl = Table([[box1, box2, box3]], colWidths=[60 * mm, 62 * mm, 62 * mm])
    sig_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 0.5, BORDER_COLOR),
        ("BOX", (1, 0), (1, 0), 0.5, BORDER_COLOR),
        ("BOX", (2, 0), (2, 0), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return sig_tbl


def generate_profit_pdf(
    shipment: Any,
    ar_lines: List[Dict[str, Any]] = None,
    ap_lines: List[Dict[str, Any]] = None,
    summary: Dict[str, Any] = None,
    sheet: Dict[str, Any] = None,
    output_path: str = None,
) -> str:
    """Generate comprehensive Enterprise Job Profitability & Operations Sheet PDF."""
    if isinstance(shipment, (int, str)) and not isinstance(shipment, dict):
        from managers.shipment_manager import get_shipment
        from managers.profit_manager import get_cost_lines, get_profit_summary
        from database.connection import get_connection
        from managers.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        with get_connection() as conn:
            with conn.cursor() as cur:
                if str(shipment).isdigit():
                    cur.execute("SELECT * FROM shipments WHERE id=%s AND tenant_id=%s", (int(shipment), tenant_id))
                else:
                    cur.execute("SELECT * FROM shipments WHERE job_no=%s AND tenant_id=%s", (str(shipment), tenant_id))
                r = cur.fetchone()
                shipment = dict(r) if r else {}
        if shipment:
            s_id = shipment.get("id")
            if ar_lines is None:
                ar_lines = get_cost_lines(s_id, "AR")
            if ap_lines is None:
                ap_lines = get_cost_lines(s_id, "AP")
            if summary is None:
                summary = get_profit_summary(s_id)

    shipment = shipment or {}
    sheet = sheet or {}
    summary = summary or {}
    ar_lines = ar_lines or []
    ap_lines = ap_lines or []

    job_no = _s(shipment.get("job_no"), "JOB")
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"PROFIT_{job_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=13 * mm,
        rightMargin=13 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"Job Profitability Sheet {job_no}",
        author=COMPANY.get("name", "NATTAYAARAT CO., LTD."),
    )

    styles = _styles()
    story = []

    story.append(_header(styles))
    story.append(Spacer(1, 2.5 * mm))
    story.append(Paragraph("JOB PROFITABILITY & OPERATION SHEET", styles["title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", styles["subtitle"]))
    story.append(Spacer(1, 2.5 * mm))

    # 1. Master Job & Routing Context
    story.append(_job_info_grid(shipment, sheet, styles))
    story.append(Spacer(1, 3.0 * mm))

    # 2. AR (Revenue / Selling) Table
    ar_tot = sum(float(x.get("amount_thb") or x.get("amount", 0) or 0) for x in ar_lines)
    story.append(_cost_table(
        "REVENUE / SELLING CHARGES (AR — ลูกหนี้ / รายได้)",
        ar_lines, BRAND_NAVY, styles, "TOTAL REVENUE (AR)", is_ar=True
    ))
    story.append(Spacer(1, 2.5 * mm))

    # 3. AP (Cost / Supplier) Table
    ap_tot = sum(float(x.get("amount_thb") or x.get("amount", 0) or 0) for x in ap_lines)
    story.append(_cost_table(
        "DIRECT COSTS / SUPPLIER EXPENSES (AP — เจ้าหนี้ / ต้นทุน)",
        ap_lines, colors.HexColor("#334155"), styles, "TOTAL DIRECT COST (AP)", is_ar=False
    ))
    story.append(Spacer(1, 3.0 * mm))

    # 4. Financial KPI Summary Card
    story.append(_summary_card(summary, ar_tot, ap_tot, styles))
    story.append(Spacer(1, 3.5 * mm))

    # 5. Triple Sign-Off Block
    story.append(_signature_block(styles))

    doc.build(story)
    return output_path
