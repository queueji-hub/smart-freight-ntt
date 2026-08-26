"""Financial Reports & Statements PDF Generator.

Provides enterprise-grade document exports for:
- Daily Cash Flow & Liquidity Report (รายงานกระแสเงินสดประจำวัน)
- Daily Receipts / Collection Register (รายงานตรวจสอบการรับเงินประจำวัน)
- Daily Payment Vouchers / Disbursement Register (รายงานตรวจสอบการจ่ายเงินประจำวัน)
- Value Added Tax ภ.พ. 30 Reports (รายงานภาษีขาย และรายงานภาษีซื้อ)
- Withholding Tax ภ.ง.ด. 3 / 53 / 50 ทวิ Summary
"""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.utils import ImageReader

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

BRAND_NAVY = colors.HexColor("#0F294A")
BRAND_BLUE = colors.HexColor("#1D4ED8")
BLUE_LIGHT = colors.HexColor("#EFF6FF")
TEXT_DARK = colors.HexColor("#0F172A")
BORDER_COLOR = colors.HexColor("#CBD5E1")
HEADER_BG = colors.HexColor("#1E3A8A")
ROW_ALT = colors.HexColor("#F8FAFC")


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
        "company_th": ParagraphStyle("p_comp_th", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=11, leading=14, textColor=BRAND_NAVY),
        "company_en": ParagraphStyle("p_comp_en", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9, leading=11.5, textColor=BRAND_NAVY),
        "company_addr": ParagraphStyle("p_comp_addr", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.5, textColor=TEXT_DARK),
        "title": ParagraphStyle("p_title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=13.0, leading=16, textColor=BRAND_NAVY, alignment=TA_RIGHT),
        "subtitle": ParagraphStyle("p_sub", parent=base["Normal"], fontName=THAI_FONT, fontSize=8.5, leading=11, textColor=BRAND_BLUE, alignment=TA_RIGHT),
        "th_center": ParagraphStyle("p_th_center", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=colors.white),
        "th_left": ParagraphStyle("p_th_left", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_LEFT, textColor=colors.white),
        "th_right": ParagraphStyle("p_th_right", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_RIGHT, textColor=colors.white),
        "td_center": ParagraphStyle("p_td_center", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_CENTER, textColor=TEXT_DARK),
        "td_left": ParagraphStyle("p_td_left", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_LEFT, textColor=TEXT_DARK),
        "td_right": ParagraphStyle("p_td_right", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "td_right_b": ParagraphStyle("p_td_right_b", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "td_center_b": ParagraphStyle("p_td_center_b", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "sign_role": ParagraphStyle("p_sign_role", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=BRAND_NAVY),
        "sign_date": ParagraphStyle("p_sign_date", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.5, leading=8.5, alignment=TA_CENTER, textColor=colors.HexColor("#64748B")),
    }


def _build_header(st, report_title: str, report_subtitle: str, width_l: float = 110, width_r: float = 80):
    logo_path = Path("assets/logo.png")
    if not logo_path.exists():
        logo_path = Path("assets/logo.jpg")

    logo_img = ""
    if logo_path.exists():
        try:
            logo_img = Image(str(logo_path), width=36 * 2.83465, height=13 * 2.83465)
        except Exception:
            logo_img = ""

    comp_info = [
        Paragraph(f"<b>{COMPANY.get('name_th', 'บริษัท สมาร์ท เฟรท เอ็นทีที จำกัด')}</b>", st["company_th"]),
        Paragraph(COMPANY.get("name_en", "SMART FREIGHT NTT CO., LTD."), st["company_en"]),
        Paragraph(f"{COMPANY.get('address_th', '')} | เลขประจำตัวผู้เสียภาษี: {COMPANY.get('tax_id', '')}", st["company_addr"]),
    ]

    left_cell = [logo_img, Spacer(1, 2)] + comp_info if logo_img else comp_info
    right_cell = [
        Paragraph(report_title, st["title"]),
        Paragraph(report_subtitle, st["subtitle"]),
        Spacer(1, 4),
        Paragraph(f"พิมพ์เมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}", st["td_right"]),
    ]

    header_table = Table([[left_cell, right_cell]], colWidths=[width_l * 2.83465, width_r * 2.83465])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    return header_table


def _build_signoffs(st, roles=None, total_width=190):
    roles = roles or [
        ("ผู้จัดทำ (Prepared By)", "Date: ___/___/______"),
        ("ผู้ตรวจสอบ (Verified By)", "Date: ___/___/______"),
        ("ผู้จัดการฝ่ายการเงิน / อนุมัติ (Approved By)", "Date: ___/___/______"),
    ]
    col_w = total_width / len(roles)
    cols = []
    for r_title, r_sub in roles:
        cell = [
            Spacer(1, 22),
            Paragraph("____________________________", st["td_center"]),
            Spacer(1, 3),
            Paragraph(r_title, st["sign_role"]),
            Paragraph(r_sub, st["sign_date"]),
        ]
        cols.append(cell)

    t = Table([cols], colWidths=[col_w * 2.83465] * len(roles))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# =========================================================
# 1. DAILY CASH FLOW & LIQUIDITY PDF
# =========================================================
def generate_daily_cashflow_pdf(
    as_of_date: str,
    metrics: Dict[str, float],
    inflow_items: List[Dict[str, Any]],
    outflow_items: List[Dict[str, Any]]
) -> str:
    st = _styles()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"CashFlow_Daily_{as_of_date.replace('-', '')}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=10 * 2.83465, rightMargin=10 * 2.83465,
        topMargin=10 * 2.83465, bottomMargin=10 * 2.83465
    )

    story = []
    story.append(_build_header(st, "DAILY CASH FLOW & LIQUIDITY REPORT", f"รายงานกระแสเงินสดและสภาพคล่องประจำวัน ณ วันที่ {as_of_date}", 115, 75))
    story.append(Spacer(1, 8))

    # Summary KPI cards table
    kpi_data = [
        [
            Paragraph("<b>Cash Inflow (เงินรับชำระ)</b>", st["td_center"]),
            Paragraph("<b>Cash Outflow (เงินจ่ายชำระ)</b>", st["td_center"]),
            Paragraph("<b>Net Realized Cash (เงินสดสุทธิ)</b>", st["td_center"]),
            Paragraph("<b>Projected Position (ประมาณการ)</b>", st["td_center"]),
        ],
        [
            Paragraph(f"<b>฿ {_money(metrics.get('inflow', 0))}</b>", st["td_center_b"]),
            Paragraph(f"<b>฿ {_money(metrics.get('outflow', 0))}</b>", st["td_center_b"]),
            Paragraph(f"<b>฿ {_money(metrics.get('net_realized', 0))}</b>", st["td_center_b"]),
            Paragraph(f"<b>฿ {_money(metrics.get('projected', 0))}</b>", st["td_center_b"]),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[47.5 * 2.83465] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_LIGHT),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))

    # INFLOW SECTION
    story.append(Paragraph("<b>📥 Cash Inflows / Collections (รายการเงินรับชำระจากลูกค้า)</b>", st["company_en"]))
    story.append(Spacer(1, 3))
    inflow_headers = [
        Paragraph("No.", st["th_center"]),
        Paragraph("Receipt / Inv No.", st["th_left"]),
        Paragraph("Customer (ลูกค้า)", st["th_left"]),
        Paragraph("Job No.", st["th_center"]),
        Paragraph("Amount (THB)", st["th_right"]),
        Paragraph("VAT 7%", st["th_right"]),
        Paragraph("WHT", st["th_right"]),
        Paragraph("Net Received", st["th_right"]),
    ]
    inflow_rows = [inflow_headers]
    tot_in_net = 0.0
    for idx, r in enumerate(inflow_items, 1):
        net = float(r.get("net_payable") or r.get("grand_total") or r.get("amount") or 0)
        tot_in_net += net
        inflow_rows.append([
            Paragraph(str(idx), st["td_center"]),
            Paragraph(_s(r.get("doc_no")), st["td_left"]),
            Paragraph(_s(r.get("customer_name")), st["td_left"]),
            Paragraph(_s(r.get("job_no")), st["td_center"]),
            Paragraph(_money(r.get("grand_total") or r.get("subtotal")), st["td_right"]),
            Paragraph(_money(r.get("vat_7_amount") or r.get("vat_amount")), st["td_right"]),
            Paragraph(_money(r.get("wht_amount")), st["td_right"]),
            Paragraph(_money(net), st["td_right_b"]),
        ])
    if len(inflow_items) == 0:
        inflow_rows.append([Paragraph("— ไม่มีรายการรับชำระในวันนี้ —", st["td_center"])] + [Paragraph("", st["td_center"])] * 7)

    inflow_rows.append([
        Paragraph("<b>ยอดรวมรับชำระทั้งสิ้น:</b>", st["td_right_b"]), "", "", "", "", "", "",
        Paragraph(f"<b>฿ {_money(tot_in_net)}</b>", st["td_right_b"])
    ])

    t_in = Table(inflow_rows, colWidths=[8 * 2.83465, 26 * 2.83465, 52 * 2.83465, 22 * 2.83465, 20 * 2.83465, 16 * 2.83465, 16 * 2.83465, 30 * 2.83465])
    t_in.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("SPAN", (0, -1), (6, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), BLUE_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_in)
    story.append(Spacer(1, 10))

    # OUTFLOW SECTION
    story.append(Paragraph("<b>📤 Cash Outflows / Disbursements (รายการเงินจ่ายสายเรือ / ค่าใช้จ่าย / เจ้าหนี้)</b>", st["company_en"]))
    story.append(Spacer(1, 3))
    outflow_headers = [
        Paragraph("No.", st["th_center"]),
        Paragraph("PV / Voucher No.", st["th_left"]),
        Paragraph("Payee / Supplier (ผู้รับเงิน)", st["th_left"]),
        Paragraph("Payment Type", st["th_left"]),
        Paragraph("Job No.", st["th_center"]),
        Paragraph("Subtotal", st["th_right"]),
        Paragraph("VAT 7%", st["th_right"]),
        Paragraph("WHT", st["th_right"]),
        Paragraph("Net Disbursed", st["th_right"]),
    ]
    outflow_rows = [outflow_headers]
    tot_out_net = 0.0
    for idx, r in enumerate(outflow_items, 1):
        net = float(r.get("net_payable") or r.get("total") or 0)
        tot_out_net += net
        outflow_rows.append([
            Paragraph(str(idx), st["td_center"]),
            Paragraph(_s(r.get("voucher_no")), st["td_left"]),
            Paragraph(_s(r.get("vendor_name") or r.get("payee_name")), st["td_left"]),
            Paragraph(_s(r.get("payment_type"), "General"), st["td_left"]),
            Paragraph(_s(r.get("job_no")), st["td_center"]),
            Paragraph(_money(r.get("subtotal")), st["td_right"]),
            Paragraph(_money(r.get("tax")), st["td_right"]),
            Paragraph(_money(r.get("wht_total")), st["td_right"]),
            Paragraph(_money(net), st["td_right_b"]),
        ])
    if len(outflow_items) == 0:
        outflow_rows.append([Paragraph("— ไม่มีรายการจ่ายชำระในวันนี้ —", st["td_center"])] + [Paragraph("", st["td_center"])] * 8)

    outflow_rows.append([
        Paragraph("<b>ยอดรวมจ่ายชำระทั้งสิ้น:</b>", st["td_right_b"]), "", "", "", "", "", "", "",
        Paragraph(f"<b>฿ {_money(tot_out_net)}</b>", st["td_right_b"])
    ])

    t_out = Table(outflow_rows, colWidths=[8 * 2.83465, 24 * 2.83465, 42 * 2.83465, 24 * 2.83465, 18 * 2.83465, 18 * 2.83465, 14 * 2.83465, 14 * 2.83465, 28 * 2.83465])
    t_out.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("SPAN", (0, -1), (7, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEF2F2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_out)
    story.append(Spacer(1, 14))

    story.append(_build_signoffs(st, total_width=190))
    doc.build(story)
    return pdf_path


# =========================================================
# 2. DAILY RECEIPTS / COLLECTION REGISTER PDF
# =========================================================
def generate_daily_receipts_pdf(as_of_date: str, receipts: List[Dict[str, Any]]) -> str:
    st = _styles()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"Daily_Receipts_{as_of_date.replace('-', '')}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=landscape(A4),
        leftMargin=10 * 2.83465, rightMargin=10 * 2.83465,
        topMargin=10 * 2.83465, bottomMargin=10 * 2.83465
    )

    story = []
    story.append(_build_header(st, "DAILY RECEIPT & COLLECTION REGISTER", f"ทะเบียนตรวจสอบการรับเงินประจำวัน ณ วันที่ {as_of_date}", 180, 97))
    story.append(Spacer(1, 8))

    headers = [
        Paragraph("No.", st["th_center"]),
        Paragraph("Receipt No.", st["th_left"]),
        Paragraph("Tax Inv No.", st["th_left"]),
        Paragraph("Customer Name (ลูกค้า)", st["th_left"]),
        Paragraph("Job No.", st["th_center"]),
        Paragraph("Service Type", st["th_left"]),
        Paragraph("Tax Base", st["th_right"]),
        Paragraph("VAT 7%", st["th_right"]),
        Paragraph("WHT", st["th_right"]),
        Paragraph("Net Collected (THB)", st["th_right"]),
        Paragraph("Payment Status", st["th_center"]),
    ]
    rows = [headers]
    tot_base, tot_vat, tot_wht, tot_net = 0.0, 0.0, 0.0, 0.0

    for idx, r in enumerate(receipts, 1):
        base = float(r.get("amount_vat") or r.get("subtotal") or 0)
        vat = float(r.get("vat_7_amount") or r.get("vat_amount") or 0)
        wht = float(r.get("wht_amount") or 0)
        net = float(r.get("net_payable") or r.get("grand_total") or (base + vat - wht))

        tot_base += base
        tot_vat += vat
        tot_wht += wht
        tot_net += net

        rows.append([
            Paragraph(str(idx), st["td_center"]),
            Paragraph(_s(r.get("doc_no")), st["td_left"]),
            Paragraph(_s(r.get("tax_receipt_no") or r.get("doc_no")), st["td_left"]),
            Paragraph(_s(r.get("customer_name")), st["td_left"]),
            Paragraph(_s(r.get("job_no")), st["td_center"]),
            Paragraph(_s(r.get("service_type"), "Freight"), st["td_left"]),
            Paragraph(_money(base), st["td_right"]),
            Paragraph(_money(vat), st["td_right"]),
            Paragraph(_money(wht), st["td_right"]),
            Paragraph(_money(net), st["td_right_b"]),
            Paragraph(_s(r.get("payment_status"), "PAID"), st["td_center"]),
        ])

    if len(receipts) == 0:
        rows.append([Paragraph("— ไม่มีรายการรับชำระในวันนี้ —", st["td_center"])] + [Paragraph("", st["td_center"])] * 10)

    rows.append([
        Paragraph("<b>รวมทั้งสิ้น (Grand Total):</b>", st["td_right_b"]), "", "", "", "", "",
        Paragraph(f"<b>{_money(tot_base)}</b>", st["td_right_b"]),
        Paragraph(f"<b>{_money(tot_vat)}</b>", st["td_right_b"]),
        Paragraph(f"<b>{_money(tot_wht)}</b>", st["td_right_b"]),
        Paragraph(f"<b>฿ {_money(tot_net)}</b>", st["td_right_b"]),
        ""
    ])

    t = Table(rows, colWidths=[10 * 2.83465, 26 * 2.83465, 26 * 2.83465, 60 * 2.83465, 24 * 2.83465, 30 * 2.83465, 22 * 2.83465, 20 * 2.83465, 18 * 2.83465, 28 * 2.83465, 18 * 2.83465])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("SPAN", (0, -1), (5, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), BLUE_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(_build_signoffs(st, total_width=277))
    doc.build(story)
    return pdf_path


# =========================================================
# 3. DAILY PAYMENT VOUCHERS / DISBURSEMENT REGISTER PDF
# =========================================================
def generate_daily_payments_pdf(as_of_date: str, vouchers: List[Dict[str, Any]]) -> str:
    st = _styles()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"Daily_Payments_{as_of_date.replace('-', '')}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=landscape(A4),
        leftMargin=10 * 2.83465, rightMargin=10 * 2.83465,
        topMargin=10 * 2.83465, bottomMargin=10 * 2.83465
    )

    story = []
    story.append(_build_header(st, "DAILY PAYMENT VOUCHER & DISBURSEMENT REGISTER", f"ทะเบียนตรวจสอบการจ่ายเงินประจำวัน ณ วันที่ {as_of_date}", 180, 97))
    story.append(Spacer(1, 8))

    headers = [
        Paragraph("No.", st["th_center"]),
        Paragraph("PV No.", st["th_left"]),
        Paragraph("Vendor / Payee (ผู้รับเงิน)", st["th_left"]),
        Paragraph("Tax ID", st["th_center"]),
        Paragraph("Job No.", st["th_center"]),
        Paragraph("Payment Type", st["th_left"]),
        Paragraph("Paid By", st["th_center"]),
        Paragraph("Subtotal", st["th_right"]),
        Paragraph("VAT 7%", st["th_right"]),
        Paragraph("WHT", st["th_right"]),
        Paragraph("Net Disbursed (THB)", st["th_right"]),
    ]
    rows = [headers]
    tot_sub, tot_vat, tot_wht, tot_net = 0.0, 0.0, 0.0, 0.0

    for idx, r in enumerate(vouchers, 1):
        sub = float(r.get("subtotal") or 0)
        vat = float(r.get("tax") or 0)
        wht = float(r.get("wht_total") or 0)
        net = float(r.get("net_payable") or r.get("total") or (sub + vat - wht))

        tot_sub += sub
        tot_vat += vat
        tot_wht += wht
        tot_net += net

        rows.append([
            Paragraph(str(idx), st["td_center"]),
            Paragraph(_s(r.get("voucher_no")), st["td_left"]),
            Paragraph(_s(r.get("vendor_name") or r.get("payee_name")), st["td_left"]),
            Paragraph(_s(r.get("vendor_tax_id") or r.get("payee_tax_id")), st["td_center"]),
            Paragraph(_s(r.get("job_no")), st["td_center"]),
            Paragraph(_s(r.get("payment_type"), "General"), st["td_left"]),
            Paragraph(_s(r.get("paid_by"), "Transfer"), st["td_center"]),
            Paragraph(_money(sub), st["td_right"]),
            Paragraph(_money(vat), st["td_right"]),
            Paragraph(_money(wht), st["td_right"]),
            Paragraph(_money(net), st["td_right_b"]),
        ])

    if len(vouchers) == 0:
        rows.append([Paragraph("— ไม่มีรายการจ่ายชำระในวันนี้ —", st["td_center"])] + [Paragraph("", st["td_center"])] * 10)

    rows.append([
        Paragraph("<b>รวมทั้งสิ้น (Grand Total):</b>", st["td_right_b"]), "", "", "", "", "", "",
        Paragraph(f"<b>{_money(tot_sub)}</b>", st["td_right_b"]),
        Paragraph(f"<b>{_money(tot_vat)}</b>", st["td_right_b"]),
        Paragraph(f"<b>{_money(tot_wht)}</b>", st["td_right_b"]),
        Paragraph(f"<b>฿ {_money(tot_net)}</b>", st["td_right_b"]),
    ])

    t = Table(rows, colWidths=[10 * 2.83465, 26 * 2.83465, 58 * 2.83465, 26 * 2.83465, 22 * 2.83465, 28 * 2.83465, 20 * 2.83465, 22 * 2.83465, 18 * 2.83465, 18 * 2.83465, 30 * 2.83465])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("SPAN", (0, -1), (6, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEF2F2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(_build_signoffs(st, total_width=277))
    doc.build(story)
    return pdf_path


# =========================================================
# 4. VALUE ADDED TAX (ภ.พ. 30) PDF (SALES / PURCHASE)
# =========================================================
def generate_vat_report_pdf(report_type: str, records: List[Dict[str, Any]]) -> str:
    is_sales = "SALE" in report_type.upper() or "OUTPUT" in report_type.upper() or "ขาย" in report_type
    st = _styles()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prefix = "Output_VAT_Sales" if is_sales else "Input_VAT_Purchases"
    filename = f"{prefix}_Report_{date.today().strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=landscape(A4),
        leftMargin=10 * 2.83465, rightMargin=10 * 2.83465,
        topMargin=10 * 2.83465, bottomMargin=10 * 2.83465
    )

    title = "OUTPUT VAT REPORT (รายงานภาษีขาย ภ.พ. 30)" if is_sales else "INPUT VAT REPORT (รายงานภาษีซื้อ ภ.พ. 30)"
    subtitle = "รายงานภาษีมูลค่าเพิ่ม สำหรับยื่นแบบ ภ.พ. 30 ต่อกรมสรรพากร"

    story = []
    story.append(_build_header(st, title, subtitle, 180, 97))
    story.append(Spacer(1, 8))

    party_header = "Customer Name (ชื่อผู้ซื้อ/บริการ)" if is_sales else "Supplier Name (ชื่อผู้ขาย/ผู้ให้บริการ)"
    inv_header = "Tax Invoice No. (เลขที่ใบกำกับ)" if is_sales else "Supplier Tax Inv (เลขที่ใบกำกับภาษี)"

    headers = [
        Paragraph("No.", st["th_center"]),
        Paragraph("Date", st["th_center"]),
        Paragraph(inv_header, st["th_left"]),
        Paragraph(party_header, st["th_left"]),
        Paragraph("Tax ID (13 หลัก)", st["th_center"]),
        Paragraph("Branch", st["th_center"]),
        Paragraph("Tax Base (มูลค่าสินค้า/บริการ)", st["th_right"]),
        Paragraph("VAT 7% (ภาษีมูลค่าเพิ่ม)", st["th_right"]),
        Paragraph("Total Amount (ยอดรวม)", st["th_right"]),
    ]
    rows = [headers]
    tot_base, tot_vat, tot_amt = 0.0, 0.0, 0.0

    for idx, r in enumerate(records, 1):
        base = float(r.get("Tax Base (มูลค่าสินค้า/บริการ)") or r.get("base") or 0)
        vat = float(r.get("Output VAT 7% (ภาษีมูลค่าเพิ่ม)") or r.get("Input VAT 7% (ภาษีซื้อ)") or r.get("vat") or 0)
        total = float(r.get("Total") or (base + vat))

        tot_base += base
        tot_vat += vat
        tot_amt += total

        rows.append([
            Paragraph(str(idx), st["td_center"]),
            Paragraph(_s(r.get("Date")), st["td_center"]),
            Paragraph(_s(r.get("Tax Invoice No.") or r.get("Supplier Tax Inv No.") or r.get("inv_no")), st["td_left"]),
            Paragraph(_s(r.get("Customer Name") or r.get("Supplier Name") or r.get("name")), st["td_left"]),
            Paragraph(_s(r.get("Tax ID")), st["td_center"]),
            Paragraph(_s(r.get("Branch"), "00000"), st["td_center"]),
            Paragraph(_money(base), st["td_right"]),
            Paragraph(_money(vat), st["td_right"]),
            Paragraph(_money(total), st["td_right_b"]),
        ])

    if len(records) == 0:
        rows.append([Paragraph("— ไม่มีรายการภาษี —", st["td_center"])] + [Paragraph("", st["td_center"])] * 8)

    rows.append([
        Paragraph("<b>รวมทั้งสิ้น (Grand Total):</b>", st["td_right_b"]), "", "", "", "", "",
        Paragraph(f"<b>{_money(tot_base)}</b>", st["td_right_b"]),
        Paragraph(f"<b>{_money(tot_vat)}</b>", st["td_right_b"]),
        Paragraph(f"<b>฿ {_money(tot_amt)}</b>", st["td_right_b"]),
    ])

    t = Table(rows, colWidths=[10 * 2.83465, 20 * 2.83465, 36 * 2.83465, 75 * 2.83465, 30 * 2.83465, 16 * 2.83465, 30 * 2.83465, 28 * 2.83465, 32 * 2.83465])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG if is_sales else BRAND_NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("SPAN", (0, -1), (5, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), BLUE_LIGHT if is_sales else colors.HexColor("#FEF2F2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(_build_signoffs(st, total_width=277))
    doc.build(story)
    return pdf_path


# =========================================================
# 5. WITHHOLDING TAX (50 ทวิ & ภ.ง.ด. 3/53) PDF
# =========================================================
def generate_wht_report_pdf(pnd_type: str, records: List[Dict[str, Any]]) -> str:
    st = _styles()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"WHT_PND_{pnd_type}_Report_{date.today().strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=landscape(A4),
        leftMargin=10 * 2.83465, rightMargin=10 * 2.83465,
        topMargin=10 * 2.83465, bottomMargin=10 * 2.83465
    )

    pnd_label = "ภ.ง.ด. 53 (จ่ายนิติบุคคล)" if "53" in str(pnd_type) else "ภ.ง.ด. 3 (จ่ายบุคคลธรรมดา)"
    title = f"WITHHOLDING TAX REPORT / รายงานภาษีหัก ณ ที่จ่าย ({pnd_label})"
    subtitle = "สรุปรายการหนังสือรับรองการหักภาษี ณ ที่จ่าย (มาตรา 50 ทวิ)"

    story = []
    story.append(_build_header(st, title, subtitle, 180, 97))
    story.append(Spacer(1, 8))

    headers = [
        Paragraph("No.", st["th_center"]),
        Paragraph("Date", st["th_center"]),
        Paragraph("50 ทวิ No.", st["th_left"]),
        Paragraph("Payee Name (ผู้ถูกหักภาษี)", st["th_left"]),
        Paragraph("Tax ID (13 หลัก)", st["th_center"]),
        Paragraph("Payment Type (ประเภทเงินได้)", st["th_left"]),
        Paragraph("Base Amount (เงินได้ที่จ่าย)", st["th_right"]),
        Paragraph("Tax Deducted (ภาษีที่หัก)", st["th_right"]),
    ]
    rows = [headers]
    tot_base, tot_tax = 0.0, 0.0

    for idx, r in enumerate(records, 1):
        base = float(r.get("Base Amount (เงินได้ที่จ่าย)") or r.get("Base Amount") or 0)
        tax = float(r.get("Tax Deducted (ภาษีที่หัก)") or r.get("Tax Deducted") or 0)

        tot_base += base
        tot_tax += tax

        rows.append([
            Paragraph(str(idx), st["td_center"]),
            Paragraph(_s(r.get("Date")), st["td_center"]),
            Paragraph(_s(r.get("50 ทวิ No.")), st["td_left"]),
            Paragraph(_s(r.get("Payee Name (ผู้ถูกหัก)") or r.get("Payee Name")), st["td_left"]),
            Paragraph(_s(r.get("Tax ID (13 หลัก)") or r.get("Tax ID")), st["td_center"]),
            Paragraph(_s(r.get("Payment Type"), "Service"), st["td_left"]),
            Paragraph(_money(base), st["td_right"]),
            Paragraph(_money(tax), st["td_right_b"]),
        ])

    if len(records) == 0:
        rows.append([Paragraph("— ไม่มีรายการภาษีหัก ณ ที่จ่าย —", st["td_center"])] + [Paragraph("", st["td_center"])] * 7)

    rows.append([
        Paragraph("<b>รวมทั้งสิ้น (Grand Total):</b>", st["td_right_b"]), "", "", "", "", "",
        Paragraph(f"<b>฿ {_money(tot_base)}</b>", st["td_right_b"]),
        Paragraph(f"<b>฿ {_money(tot_tax)}</b>", st["td_right_b"]),
    ])

    t = Table(rows, colWidths=[10 * 2.83465, 20 * 2.83465, 34 * 2.83465, 80 * 2.83465, 34 * 2.83465, 35 * 2.83465, 32 * 2.83465, 32 * 2.83465])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("SPAN", (0, -1), (5, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), BLUE_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(_build_signoffs(st, total_width=277))
    doc.build(story)
    return pdf_path
