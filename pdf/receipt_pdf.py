"""Receipt / Tax Invoice PDF template matching the supplied company reference.

Designed for the official NATTAYAARAT CO., LTD. (บริษัท ณัฐยาราชย์ จำกัด) workflow:
- Green financial visual language (#16A34A / #15803D / #86EFAC / #F0FDF4)
- 2-page document: Page 1 Original (ต้นฉบับ/Original), Page 2 Copy (สำเนา/Copy)
- Company header: Thai/English name, Head office address, Tax ID: 0735568004823, Tel
- Customer box: Pastel green background, customer details on left, document metadata on right
- Shipping address box: สถานที่จัดส่ง / Shipping Address & Page number
- 7-Column Line Items table: No., Description, Quantity, Unit, Unit Price, Discount %, Amount
- Totals & Grand Net Total with Thai Baht Words
- 4-Box Signatures Block: Payer, Receiver, Company Stamp, Authorized Signature
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.utils import ImageReader

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD
from utils.number_to_words import thai_baht_text, number_to_english_words

GREEN_PRIMARY = colors.HexColor("#16A34A")
GREEN_DARK = colors.HexColor("#15803D")
GREEN_LIGHT = colors.HexColor("#F0FDF4")
GREEN_BORDER = colors.HexColor("#86EFAC")
TEXT_DARK = colors.HexColor("#0F172A")
MUTED_GRAY = colors.HexColor("#64748B")
LINE_GRAY = colors.HexColor("#CBD5E1")

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]


def _fmt_thai_date(value) -> str:
    if not value:
        return ""
    dt = None
    if isinstance(value, (date, datetime)):
        dt = value
    else:
        try:
            dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except Exception:
            return str(value)
    
    day = dt.day
    month = THAI_MONTHS[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
    year = dt.year
    if year < 2400:
        year += 543
    return f"{day} {month} {year}"


def _money(value) -> str:
    try:
        return f"{float(value or 0):,.2f}"
    except Exception:
        return "0.00"


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "company_th": ParagraphStyle("rc_comp_th", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9.5, leading=12, textColor=TEXT_DARK),
        "company_en": ParagraphStyle("rc_comp_en", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=11, textColor=TEXT_DARK),
        "company_addr": ParagraphStyle("rc_comp_addr", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.5, textColor=TEXT_DARK),
        "orig_copy_dark": ParagraphStyle("rc_orig_copy", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9.5, leading=12, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "orig_copy_sub": ParagraphStyle("rc_orig_sub", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.0, leading=10, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "doc_title_th": ParagraphStyle("rc_doc_title_th", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=11.5, leading=14, alignment=TA_RIGHT, textColor=GREEN_PRIMARY),
        "doc_title_en": ParagraphStyle("rc_doc_title_en", parent=base["Normal"], fontName=THAI_FONT, fontSize=8.5, leading=11, alignment=TA_RIGHT, textColor=GREEN_PRIMARY),
        
        "cust_head": ParagraphStyle("rc_cust_head", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.2, leading=10.5, textColor=TEXT_DARK),
        "cust_name": ParagraphStyle("rc_cust_name", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.2, leading=10.5, textColor=TEXT_DARK),
        "cust_text": ParagraphStyle("rc_cust_text", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, textColor=TEXT_DARK),
        
        "meta_label": ParagraphStyle("rc_meta_label", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "meta_val": ParagraphStyle("rc_meta_val", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        
        "ship_addr_label": ParagraphStyle("rc_ship_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "ship_addr_val": ParagraphStyle("rc_ship_val", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "page_label": ParagraphStyle("rc_page_label", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.5, leading=9.5, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "th_center": ParagraphStyle("rc_th_center", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "th_left": ParagraphStyle("rc_th_left", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_LEFT, textColor=TEXT_DARK),
        "th_right": ParagraphStyle("rc_th_right", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "td_center": ParagraphStyle("rc_td_center", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "td_left": ParagraphStyle("rc_td_left", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_LEFT, textColor=TEXT_DARK),
        "td_right": ParagraphStyle("rc_td_right", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "tot_label": ParagraphStyle("rc_tot_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.0, leading=10, textColor=TEXT_DARK),
        "tot_val": ParagraphStyle("rc_tot_val", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.0, leading=10, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "net_label": ParagraphStyle("rc_net_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9.0, leading=11, textColor=TEXT_DARK),
        "net_val": ParagraphStyle("rc_net_val", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9.5, leading=12, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "thai_words": ParagraphStyle("rc_thai_words", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.0, leading=10, alignment=TA_CENTER, textColor=TEXT_DARK),
        
        "sign_role": ParagraphStyle("rc_sign_role", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "sign_date": ParagraphStyle("rc_sign_date", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "sign_comp": ParagraphStyle("rc_sign_comp", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.0, leading=8.5, alignment=TA_CENTER, textColor=GREEN_PRIMARY),
    }


def _header(styles: Dict[str, ParagraphStyle], copy_label: str) -> Table:
    logo_path = COMPANY.get("logo_path")
    logo = None
    if logo_path and Path(logo_path).exists():
        try:
            ir = ImageReader(str(logo_path))
            iw, ih = ir.getSize()
            scale = min(34 * mm / iw, 19 * mm / ih)
            logo = Image(str(logo_path), width=iw * scale, height=ih * scale)
        except Exception:
            logo = None
    if logo is None:
        logo = Paragraph("<b>NATTAYAARAT</b>", styles["company_th"])

    comp_th = "บริษัท ณัฐยาราชย์ จำกัด (สำนักงานใหญ่)"
    comp_en = "NATTAYAARAT CO.,LTD. (Head Office)"
    addr_line1 = "เลขที่ 59/9 หมู่ที่ 4 ตำบลบางกระทึก อำเภอสามพราน จังหวัดนครปฐม 73210"
    tax_id_line = f"เลขประจำตัวผู้เสียภาษี {COMPANY.get('tax_id', '0735568004823')}"
    tel_line = f"โทร: {COMPANY.get('tel', '')}"

    address_paragraphs = [
        Paragraph(f"<b>{comp_th}</b>", styles["company_th"]),
        Paragraph(f"<b>{comp_en}</b>", styles["company_en"]),
        Paragraph(addr_line1, styles["company_addr"]),
        Paragraph(tax_id_line, styles["company_addr"]),
        Paragraph(tel_line, styles["company_addr"]),
    ]

    if copy_label == "copy":
        top_badge_1 = "ไม่ใช่ใบกำกับภาษี"
        top_badge_2 = "สำเนา/Copy"
    else:
        top_badge_1 = "ใบกำกับภาษี"
        top_badge_2 = "ต้นฉบับ/Original"

    right_paragraphs = [
        Paragraph(f"<b>{top_badge_1}</b>", styles["orig_copy_dark"]),
        Paragraph(f"<b>{top_badge_2}</b>", styles["orig_copy_sub"]),
        Spacer(1, 1.5 * mm),
        Paragraph("<b>ใบเสร็จรับเงิน/ใบกำกับภาษี</b>", styles["doc_title_th"]),
        Paragraph("Receipt/Tax Invoice", styles["doc_title_en"]),
    ]

    tbl = Table([[logo, address_paragraphs, right_paragraphs]], colWidths=[36 * mm, 90 * mm, 56 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 4),
    ]))
    return tbl


def _customer_card(invoice: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    cname = invoice.get("customer_name") or "K AND O ENGINEERING CO.,LTD. (HEAD OFFICE)"
    caddr = invoice.get("customer_address") or ""
    ctax = invoice.get("customer_tax_id") or ""
    ctel = invoice.get("customer_tel") or invoice.get("tel") or ""
    ccontact = invoice.get("contact_person") or invoice.get("attention") or ""

    left_cells = [
        Paragraph("<b>ลูกค้า / Customer</b>", styles["cust_head"]),
        Paragraph(f"<b>{cname}</b>", styles["cust_name"]),
        Paragraph(caddr, styles["cust_text"]),
        Paragraph(f"เลขที่ผู้เสียภาษี {ctax}" if ctax else "", styles["cust_text"]),
        Paragraph(f"โทร. {ctel}" if ctel else "", styles["cust_text"]),
        Paragraph(f"ติดต่อ/ประสานงาน : {ccontact}" if ccontact else "", styles["cust_text"]),
    ]
    # Filter empty paragraphs
    left_cells = [p for p in left_cells if p.text.strip()]

    doc_date = _fmt_thai_date(invoice.get("issue_date") or invoice.get("doc_date") or date.today())
    due_date = _fmt_thai_date(invoice.get("due_date") or invoice.get("issue_date") or date.today())
    doc_no = str(invoice.get("doc_no") or "RC2607-0008")
    ref_no = str(invoice.get("ref_doc_no") or invoice.get("job_no") or "—")
    credit = f"{invoice.get('credit_days', 0)} วัน"
    prepared_by = str(invoice.get("prepared_by") or invoice.get("created_by") or "PATTAMA").upper()

    right_rows = [
        [Paragraph("วันที่ / Date", styles["meta_label"]), Paragraph(f": {doc_date}", styles["meta_val"])],
        [Paragraph("เลขที่ / No.", styles["meta_label"]), Paragraph(f": {doc_no}", styles["meta_val"])],
        [Paragraph("อ้างอิง / Ref.", styles["meta_label"]), Paragraph(f": {ref_no}", styles["meta_val"])],
        [Paragraph("เครดิต (วัน) / Credit", styles["meta_label"]), Paragraph(f": {credit}", styles["meta_val"])],
        [Paragraph("ครบกำหนด / Due Date", styles["meta_label"]), Paragraph(f": {due_date}", styles["meta_val"])],
        [Paragraph("ผู้จัดทำ / Prepared By", styles["meta_label"]), Paragraph(f": {prepared_by}", styles["meta_val"])],
    ]

    right_tbl = Table(right_rows, colWidths=[36 * mm, 42 * mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.0),
    ]))

    card = Table([[left_cells, right_tbl]], colWidths=[104 * mm, 78 * mm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, GREEN_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return card


def _shipping_address_card(invoice: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    ship_addr = invoice.get("shipping_address") or "ส่งตามที่อยู่ของสถานประกอบการ"
    left = [
        Paragraph("<b>สถานที่จัดส่ง / Shipping Address:</b>", styles["ship_addr_label"]),
        Paragraph(str(ship_addr), styles["ship_addr_val"]),
    ]
    right = [
        Paragraph("<b>หน้า / Page</b>", styles["page_label"]),
        Paragraph("1 / 1", styles["page_label"]),
    ]
    tbl = Table([[left, right]], colWidths=[150 * mm, 32 * mm])
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, GREEN_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _items_table(items: List[Dict[str, Any]], styles: Dict[str, ParagraphStyle]) -> Table:
    headers = [
        Paragraph("ลำดับ<br/>No.", styles["th_center"]),
        Paragraph("รายการ<br/>Description", styles["th_left"]),
        Paragraph("จำนวน<br/>Quantity", styles["th_right"]),
        Paragraph("หน่วย<br/>Unit", styles["th_center"]),
        Paragraph("ราคา/หน่วย<br/>Unit Price", styles["th_right"]),
        Paragraph("ส่วนลด %<br/>Discount", styles["th_right"]),
        Paragraph("จำนวนเงิน<br/>Amount", styles["th_right"]),
    ]

    rows = [headers]
    for idx, item in enumerate(items or [], 1):
        desc = str(item.get("description") or item.get("item_name") or "")
        qty = float(item.get("quantity") or 1)
        unit = str(item.get("unit") or item.get("package_unit") or "")
        price = float(item.get("unit_price") or item.get("price") or 0)
        discount = float(item.get("discount_pct") or item.get("discount") or 0)
        amount = float(item.get("amount") if item.get("amount") is not None else (qty * price * (1 - discount / 100)))

        rows.append([
            Paragraph(str(idx), styles["td_center"]),
            Paragraph(desc, styles["td_left"]),
            Paragraph(f"{qty:,.2f}" if qty != 1 else "1.00", styles["td_right"]),
            Paragraph(unit, styles["td_center"]),
            Paragraph(_money(price), styles["td_right"]),
            Paragraph(f"{discount:.2f}", styles["td_right"]),
            Paragraph(_money(amount), styles["td_right"]),
        ])

    if len(rows) == 1:
        rows.append([
            Paragraph("1", styles["td_center"]),
            Paragraph("OCEAN FREIGHT", styles["td_left"]),
            Paragraph("1.00", styles["td_right"]),
            Paragraph("SHPMT", styles["td_center"]),
            Paragraph("0.00", styles["td_right"]),
            Paragraph("0.00", styles["td_right"]),
            Paragraph("0.00", styles["td_right"]),
        ])

    tbl = Table(rows, colWidths=[12 * mm, 74 * mm, 18 * mm, 16 * mm, 22 * mm, 18 * mm, 22 * mm])
    tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, GREEN_DARK),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, GREEN_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
    ]))
    return tbl


def _totals_block(invoice: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    summary = invoice.get("summary") or {}
    subtotal = float(summary.get("total_before_vat", invoice.get("subtotal", invoice.get("amount", 0))) or 0)
    vat_amt = float(summary.get("total_vat_7", invoice.get("vat_amount", 0)) or 0)
    grand_tot = float(summary.get("grand_total", invoice.get("total_amount", invoice.get("total", subtotal + vat_amt))) or 0)
    remark = str(invoice.get("remark") or invoice.get("remarks") or "")

    left_remark = [
        Paragraph("<b>หมายเหตุ / Remarks :</b>", styles["cust_head"]),
        Paragraph(remark, styles["cust_text"]),
    ]

    calc_rows = [
        [Paragraph("จำนวนเงินก่อนภาษี", styles["tot_label"]), Paragraph(_money(subtotal), styles["tot_val"])],
        [Paragraph("ภาษีมูลค่าเพิ่ม", styles["tot_label"]), Paragraph(_money(vat_amt), styles["tot_val"])],
        [Paragraph("จำนวนเงินรวมทั้งสิ้น", styles["tot_label"]), Paragraph(_money(grand_tot), styles["tot_val"])],
    ]
    calc_tbl = Table(calc_rows, colWidths=[46 * mm, 36 * mm])
    calc_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))

    sub_block = Table([[left_remark, calc_tbl]], colWidths=[100 * mm, 82 * mm])
    sub_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    thai_words_str = f"({thai_baht_text(grand_tot)})"

    net_row = [
        Paragraph("<b>จำนวนเงินรวมสุทธิ</b>", styles["net_label"]),
        Paragraph(f"<b>{_money(grand_tot)}</b>", styles["net_val"]),
    ]
    net_tbl = Table([net_row], colWidths=[100 * mm, 82 * mm])
    net_tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.HexColor("#0F172A")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor("#0F172A")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    thai_words_row = [Paragraph(thai_words_str, styles["thai_words"])]
    thai_tbl = Table([thai_words_row], colWidths=[182 * mm])
    thai_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    wrapper = Table([[sub_block], [net_tbl], [thai_tbl]], colWidths=[182 * mm])
    wrapper.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return wrapper


def _signatures_block(styles: Dict[str, ParagraphStyle]) -> Table:
    col1 = [
        Spacer(1, 11 * mm),
        Paragraph("ผู้จ่ายเงิน / Payer", styles["sign_role"]),
        Spacer(1, 1.0 * mm),
        Paragraph("วันที่/Date:____/____/______", styles["sign_date"]),
    ]
    col2 = [
        Spacer(1, 11 * mm),
        Paragraph("ผู้รับเงิน / Receiver", styles["sign_role"]),
        Spacer(1, 1.0 * mm),
        Paragraph("วันที่/Date:____/____/______", styles["sign_date"]),
    ]
    
    # Blue Company Stamp
    from config import BASE_DIR
    stamp_path = Path(BASE_DIR) / "assets" / "company_stamp_blue.png"
    if not stamp_path.exists():
        stamp_path = Path(COMPANY.get("logo_path", ""))
        
    stamp_img = None
    if stamp_path.exists():
        try:
            ir = ImageReader(str(stamp_path))
            iw, ih = ir.getSize()
            scale = min(36 * mm / iw, 21 * mm / ih)
            stamp_img = Image(str(stamp_path), width=iw * scale, height=ih * scale)
        except Exception:
            stamp_img = None

    col3 = [
        stamp_img or Spacer(1, 11 * mm),
    ]

    col4 = [
        Spacer(1, 11 * mm),
        Paragraph("ผู้มีอำนาจลงนาม", styles["sign_role"]),
        Paragraph("Authorized Signature", styles["sign_role"]),
        Spacer(1, 1.0 * mm),
        Paragraph("วันที่/Date:____/____/______", styles["sign_date"]),
    ]

    tbl = Table([[col1, col2, col3, col4]], colWidths=[45.5 * mm, 45.5 * mm, 45.5 * mm, 45.5 * mm], rowHeights=[27 * mm])
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, GREEN_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, GREEN_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def generate_receipt_pdf(invoice: Dict[str, Any], customer: Dict[str, Any] = None, output_path: str = None) -> str:
    """Generate the canonical Receipt / Tax Invoice PDF with Original + Copy pages matching the approved sample."""
    data = dict(invoice or {})
    if customer:
        data.update({
            "customer_name": customer.get("company_name") or customer.get("legal_name") or data.get("customer_name"),
            "customer_tax_id": customer.get("tax_id") or data.get("customer_tax_id"),
            "customer_address": customer.get("address") or customer.get("billing_address") or data.get("customer_address"),
            "contact_person": customer.get("contact_person") or data.get("contact_person"),
            "customer_tel": customer.get("tel") or customer.get("phone") or data.get("customer_tel"),
        })

    data.setdefault("doc_type", "RC")
    doc_no = data.get("doc_no") or "RC2607-0008"
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"RC_{doc_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    styles = _styles()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"Receipt / Tax Invoice {doc_no}",
        author=COMPANY.get("name", "NATTAYAARAT CO., LTD."),
    )

    story = []

    # 2 Pages: Page 1 = Original, Page 2 = Copy
    for copy_label in ("original", "copy"):
        story.append(_header(styles, copy_label))
        story.append(Spacer(1, 3 * mm))
        story.append(_customer_card(data, styles))
        story.append(Spacer(1, 2 * mm))
        story.append(_shipping_address_card(data, styles))
        story.append(Spacer(1, 3 * mm))
        story.append(_items_table(data.get("items", []), styles))
        story.append(Spacer(1, 4 * mm))
        story.append(_totals_block(data, styles))
        story.append(Spacer(1, 5 * mm))
        story.append(_signatures_block(styles))
        if copy_label == "original":
            story.append(PageBreak())

    doc.build(story)
    return output_path
