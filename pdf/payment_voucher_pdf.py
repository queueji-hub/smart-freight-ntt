"""Payment Voucher & Advance Request PDF Generator.

Enterprise Freight Forwarding Standard:
- Corporate Header (Smart Freight NTT)
- Document Metadata (Voucher No, Date, Job No, Payee / Vendor)
- Itemized AP Disbursement Ledger (Description, Qty, Rate, Tax Type, VAT, WHT, Net)
- Summary Box (Subtotal, VAT 7%, WHT, Net Payable)
- Quadruple Sign-off Matrix (Prepared By, Verified By, Approved By, Received By)
"""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from reportlab.lib.pagesizes import A4
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
        "title": ParagraphStyle("p_title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=14.0, leading=16, textColor=BRAND_NAVY, alignment=TA_RIGHT),
        "doc_no": ParagraphStyle("p_doc_no", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=10.0, leading=12, textColor=BRAND_BLUE, alignment=TA_RIGHT),
        "th_center": ParagraphStyle("p_th_center", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_CENTER, textColor=colors.white),
        "th_left": ParagraphStyle("p_th_left", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_LEFT, textColor=colors.white),
        "th_right": ParagraphStyle("p_th_right", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_RIGHT, textColor=colors.white),
        "label": ParagraphStyle("p_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "val": ParagraphStyle("p_val", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "td_center": ParagraphStyle("p_td_center", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "td_left": ParagraphStyle("p_td_left", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_LEFT, textColor=TEXT_DARK),
        "td_right": ParagraphStyle("p_td_right", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "td_right_b": ParagraphStyle("p_td_right_b", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "sign_role": ParagraphStyle("p_sign_role", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=BRAND_NAVY),
        "sign_date": ParagraphStyle("p_sign_date", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.5, leading=8.5, alignment=TA_CENTER, textColor=colors.HexColor("#64748B")),
    }


def generate_payment_voucher_pdf(voucher: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Generates a professional PDF for an AP Payment Voucher or Advance Request."""
    st = _styles()
    voucher_no = _s(voucher.get("voucher_no"), "PV-DRAFT")
    v_type = str(voucher.get("voucher_type", "PAYMENT_VOUCHER")).upper()
    is_advance = "ADVANCE" in v_type
    doc_title = "ADVANCE PAYMENT REQUEST / ใบขอเบิกเงินทดรองจ่าย" if is_advance else "PAYMENT VOUCHER / ใบสำคัญจ่าย"

    filename = f"{voucher_no.replace('/', '_')}.pdf"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pdf_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=12 * 2.83465,
        rightMargin=12 * 2.83465,
        topMargin=12 * 2.83465,
        bottomMargin=12 * 2.83465,
    )

    story = []

    # 1. Header
    logo_path = Path("assets/logo.png")
    if not logo_path.exists():
        logo_path = Path("assets/logo.jpg")

    logo_img = ""
    if logo_path.exists():
        try:
            img = ImageReader(str(logo_path))
            iw, ih = img.getSize()
            logo_img = Image(str(logo_path), width=35 * 2.83465, height=35 * 2.83465 * (ih / iw))
        except Exception:
            logo_img = ""

    comp_info = [
        Paragraph(f"<b>{COMPANY.get('name_th', 'บริษัท ณัฏฐยาราชย์ จำกัด')}</b>", st["company_th"]),
        Paragraph(COMPANY.get("name_en", "NATTAYARAAT CO., LTD."), st["company_en"]),
        Paragraph(f"{COMPANY.get('address_full', '')} | Tax ID: {COMPANY.get('tax_id', '')}", st["company_addr"]),
        Paragraph(f"Tel: {COMPANY.get('tel', '')} | Email: {COMPANY.get('email', '')}", st["company_addr"]),
    ]

    title_block = [
        Paragraph(doc_title, st["title"]),
        Paragraph(f"Voucher No: {voucher_no}", st["doc_no"]),
        Paragraph(f"Date: {_s(voucher.get('invoice_date') or date.today().isoformat())}", st["td_right"]),
    ]

    header_table = Table([[logo_img or "", comp_info, title_block]], colWidths=[38 * 2.83465, 80 * 2.83465, 68 * 2.83465])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 2. Metadata Block
    payee = _s(voucher.get("payee_name") or voucher.get("vendor_name"), "—")
    payee_tax_id = _s(voucher.get("payee_tax_id"), "—")
    job_no = _s(voucher.get("job_no"), "—")
    vendor_inv_ref = _s(voucher.get("vendor_invoice_refs") or voucher.get("invoice_no"), "—")
    due_date = _s(voucher.get("due_date"), "—")
    currency = _s(voucher.get("currency"), "THB")
    status = _s(voucher.get("status"), "REQUESTED")

    meta_data = [
        [
            Paragraph("<b>Paid To / ผู้รับเงิน (Payee):</b>", st["label"]), Paragraph(f"{payee} (Tax ID: {payee_tax_id})", st["val"]),
            Paragraph("<b>Job No. / เลขที่งาน:</b>", st["label"]), Paragraph(job_no, st["val"]),
        ],
        [
            Paragraph("<b>Ref Vendor Invoices / ใบแจ้งหนี้:</b>", st["label"]), Paragraph(vendor_inv_ref, st["val"]),
            Paragraph("<b>Payment Due Date / วันครบกำหนด:</b>", st["label"]), Paragraph(due_date, st["val"]),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[42 * 2.83465, 52 * 2.83465, 38 * 2.83465, 54 * 2.83465])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # 3. Itemized Table
    curr_suffix = f" ({currency})" if currency != "THB" else ""
    item_header = [
        Paragraph("No.", st["th_center"]),
        Paragraph("Description / รายละเอียดการเบิกจ่าย", st["th_left"]),
        Paragraph("Vendor Inv. No.", st["th_center"]),
        Paragraph("Qty", st["th_center"]),
        Paragraph(f"Unit Rate{curr_suffix}", st["th_right"]),
        Paragraph(f"Amount ({currency})", st["th_right"]),
        Paragraph("Tax / WHT", st["th_center"]),
        Paragraph(f"VAT 7%{curr_suffix}", st["th_right"]),
        Paragraph(f"Net Payable ({currency})", st["th_right"]),
    ]

    item_rows = [item_header]
    subtotal = 0.0
    vat_total = 0.0
    wht_total = 0.0
    net_total = 0.0

    for idx, it in enumerate(items, start=1):
        amt = float(it.get("amount") or 0)
        vat = float(it.get("vat_amount") or 0)
        wht = float(it.get("wht_amount") or 0)
        net = float(it.get("net_amount") or (amt + vat - wht))

        subtotal += amt
        vat_total += vat
        wht_total += wht
        net_total += net

        vinv = _s(it.get("vendor_invoice_no"), "—")
        tax_wht_str = f"{_s(it.get('tax_type'),'VAT')}/{_s(it.get('wht_type'),'0%')}"

        item_rows.append([
            Paragraph(str(idx), st["td_center"]),
            Paragraph(_s(it.get("description")), st["td_left"]),
            Paragraph(vinv, st["td_center"]),
            Paragraph(f"{float(it.get('quantity') or 1):g} {_s(it.get('unit'),'UNIT')}", st["td_center"]),
            Paragraph(_money(it.get("unit_price")), st["td_right"]),
            Paragraph(_money(amt), st["td_right"]),
            Paragraph(tax_wht_str, st["td_center"]),
            Paragraph(_money(vat), st["td_right"]),
            Paragraph(_money(net), st["td_right_b"]),
        ])

    table = Table(
        item_rows,
        colWidths=[8 * 2.83465, 46 * 2.83465, 24 * 2.83465, 16 * 2.83465, 16 * 2.83465, 20 * 2.83465, 18 * 2.83465, 16 * 2.83465, 22 * 2.83465]
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))

    # 4. Summary Totals Box
    sum_data = [
        ["", Paragraph("<b>Subtotal (ก่อนภาษี):</b>", st["td_right_b"]), Paragraph(f"{_money(subtotal)} {currency}", st["td_right_b"])],
        ["", Paragraph("<b>VAT 7% (ภาษีมูลค่าเพิ่ม):</b>", st["td_right_b"]), Paragraph(f"{_money(vat_total)} {currency}", st["td_right_b"])],
        ["", Paragraph("<b>Withholding Tax (หัก ณ ที่จ่าย):</b>", st["td_right_b"]), Paragraph(f"- {_money(wht_total)} {currency}", st["td_right_b"])],
        ["", Paragraph("<b>NET PAYABLE / ยอดจ่ายสุทธิ:</b>", st["td_right_b"]), Paragraph(f"<b>{_money(net_total)} {currency}</b>", st["td_right_b"])],
    ]
    sum_table = Table(sum_data, colWidths=[114 * 2.83465, 44 * 2.83465, 28 * 2.83465])
    sum_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("BACKGROUND", (1, 3), (2, 3), BLUE_LIGHT),
        ("BOX", (1, 3), (2, 3), 1, BRAND_BLUE),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 10))

    # 5. Quadruple Sign-off Matrix with 1.7-inch Company Stamp
    prep_by = _s(voucher.get("created_by"), "Operator")
    
    # 1.7-inch diagonal company stamp
    stamp_path = Path("assets/company_stamp_blue.png")
    stamp_img = None
    if stamp_path.exists():
        try:
            ir = ImageReader(str(stamp_path))
            iw, ih = ir.getSize()
            diag_pt = 1.7 * 72.0  # 122.4 pt
            aspect = ih / iw if iw > 0 else 1.0
            stamp_w = diag_pt / ((1.0 + aspect**2)**0.5)
            stamp_h = stamp_w * aspect
            stamp_img = Image(str(stamp_path), width=stamp_w, height=stamp_h)
        except Exception:
            stamp_img = None

    sign_data = [
        [
            Paragraph("<b>PREPARED BY / ผู้ขอเบิก</b>", st["sign_role"]),
            Paragraph("<b>VERIFIED BY / ผู้ตรวจสอบ</b>", st["sign_role"]),
            Paragraph("<b>APPROVED BY / ผู้อนุมัติจ่าย</b>", st["sign_role"]),
            Paragraph("<b>RECEIVED BY / ผู้รับเงิน</b>", st["sign_role"]),
        ],
        [
            Paragraph("\n\n__________________", st["sign_date"]),
            Paragraph("\n\n__________________", st["sign_date"]),
            stamp_img or Paragraph("\n\n__________________", st["sign_date"]),
            Paragraph("\n\n__________________", st["sign_date"]),
        ],
        [
            Paragraph(f"({prep_by})", st["sign_date"]),
            Paragraph("(Accountant / Finance)", st["sign_date"]),
            Paragraph("(Authorized Director)", st["sign_date"]),
            Paragraph("(Payee Signature)", st["sign_date"]),
        ],
        [
            Paragraph(f"Date: {_s(voucher.get('invoice_date') or date.today().isoformat())}", st["sign_date"]),
            Paragraph("Date: _____________", st["sign_date"]),
            Paragraph(f"Date: {_s(voucher.get('invoice_date') or date.today().isoformat())}", st["sign_date"]),
            Paragraph("Date: _____________", st["sign_date"]),
        ],
    ]
    sign_table = Table(sign_data, colWidths=[46.5 * 2.83465, 46.5 * 2.83465, 46.5 * 2.83465, 46.5 * 2.83465])
    sign_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sign_table)

    doc.build(story)
    return pdf_path
