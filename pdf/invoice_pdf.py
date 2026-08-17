"""A4 Finance document generator: Delivery Order / Invoice / Tax Invoice / Billing Note.

Designed to match the official NATTAYAARAT CO., LTD. (บริษัท ณัฐยาราชย์ จำกัด) reference:
- Royal Blue financial visual language (#1D4ED8 / #2563EB / #3B82F6 / #EFF6FF)
- 2-page document for Invoices: Page 1 Original (ต้นฉบับ/Original), Page 2 Copy (สำเนา/Copy)
- Company header: Thai/English name, Head office address, Tax ID: 0735568004823, Tel
- Customer box (BILL TO / CUSTOMER): Blue border, customer details on left
- Document details box (DOCUMENT DETAILS): Document metadata on right (Date, No, Ref B/L, Credit, Due Date, Prepared By)
- Shipping address sub-box (SHIPPING / DELIVERY ADDRESS): สถานที่จัดส่ง / Shipping Address & Page number
- 7-Column Line Items table: No., Description, Quantity, Unit, Unit Price, Discount %, Amount
- Totals & Grand Net Total (GRAND TOTAL) with Thai Baht Words (AMOUNT IN WORDS)
- 3-Box Signatures Block: Receiver (ผู้รับสินค้า), Sender (ผู้ส่งสินค้า), Authorized Signature (ผู้มีอำนาจลงนาม) with Company Stamp
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

from config import COMPANY, OUTPUT_DIR, BASE_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD
from utils.number_to_words import thai_baht_text

BLUE_PRIMARY = colors.HexColor("#2563EB")
BLUE_DARK = colors.HexColor("#1D4ED8")
BLUE_LIGHT = colors.HexColor("#F0F7FF")
BLUE_BORDER = colors.HexColor("#3B82F6")
TEXT_DARK = colors.HexColor("#0F172A")
MUTED_GRAY = colors.HexColor("#64748B")
LINE_GRAY = colors.HexColor("#CBD5E1")

DOC_TITLES = {
    "INV": ("ใบส่งของ/ใบแจ้งหนี้", "Delivery Order/Invoice"),
    "INVOICE": ("ใบส่งของ/ใบแจ้งหนี้", "Delivery Order/Invoice"),
    "ใบแจ้งหนี้": ("ใบแจ้งหนี้", "Invoice"),
    "ใบส่งของ/ใบแจ้งหนี้": ("ใบส่งของ/ใบแจ้งหนี้", "Delivery Order/Invoice"),
    "TAX": ("ใบเสร็จรับเงิน/ใบกำกับภาษี", "Receipt/Tax Invoice"),
    "BN": ("ใบวางบิล", "Billing Note"),
    "CN": ("ใบลดหนี้", "Credit Note"),
    "DN": ("ใบเพิ่มหนี้", "Debit Note"),
    "SOA": ("ใบแจ้งยอดบัญชี", "Statement of Account"),
}

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


def _safe(value, default="—") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if not text or text.lower() in {"none", "nan", "nat"} else text


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "company_th": ParagraphStyle("inv_comp_th", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9.5, leading=12.5, textColor=TEXT_DARK),
        "company_en": ParagraphStyle("inv_comp_en", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=11.5, textColor=TEXT_DARK),
        "company_addr": ParagraphStyle("inv_comp_addr", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.8, textColor=TEXT_DARK),
        
        "orig_copy_dark": ParagraphStyle("inv_orig_copy", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9.5, leading=12, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "doc_title_th": ParagraphStyle("inv_doc_title_th", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=12.5, leading=15.5, alignment=TA_RIGHT, textColor=BLUE_PRIMARY),
        "doc_title_en": ParagraphStyle("inv_doc_title_en", parent=base["Normal"], fontName=THAI_FONT, fontSize=8.5, leading=11, alignment=TA_RIGHT, textColor=BLUE_PRIMARY),
        
        "cust_head": ParagraphStyle("inv_cust_head", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.2, leading=10.5, textColor=TEXT_DARK),
        "cust_name": ParagraphStyle("inv_cust_name", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.2, leading=10.5, textColor=TEXT_DARK),
        "cust_text": ParagraphStyle("inv_cust_text", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.5, textColor=TEXT_DARK),
        
        "meta_label": ParagraphStyle("inv_meta_label", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "meta_val": ParagraphStyle("inv_meta_val", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        
        "ship_addr_label": ParagraphStyle("inv_ship_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "ship_addr_val": ParagraphStyle("inv_ship_val", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "page_label": ParagraphStyle("inv_page_label", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.5, leading=9.5, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "th_center": ParagraphStyle("inv_th_center", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "th_left": ParagraphStyle("inv_th_left", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_LEFT, textColor=TEXT_DARK),
        "th_right": ParagraphStyle("inv_th_right", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "td_center": ParagraphStyle("inv_td_center", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_CENTER, textColor=TEXT_DARK),
        "td_left": ParagraphStyle("inv_td_left", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_LEFT, textColor=TEXT_DARK),
        "td_right": ParagraphStyle("inv_td_right", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "remark_label": ParagraphStyle("inv_rmk_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, textColor=TEXT_DARK),
        "remark_val": ParagraphStyle("inv_rmk_val", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.2, leading=9.2, textColor=TEXT_DARK),
        
        "tot_label": ParagraphStyle("inv_tot_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.8, leading=10, textColor=TEXT_DARK),
        "tot_val": ParagraphStyle("inv_tot_val", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.8, leading=10, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "net_label": ParagraphStyle("inv_net_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.8, leading=11, textColor=TEXT_DARK),
        "net_val": ParagraphStyle("inv_net_val", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9.2, leading=11.5, alignment=TA_RIGHT, textColor=TEXT_DARK),
        "thai_words": ParagraphStyle("inv_thai_words", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.8, leading=10, alignment=TA_CENTER, textColor=TEXT_DARK),
        
        "sign_role": ParagraphStyle("inv_sign_role", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "sign_date": ParagraphStyle("inv_sign_date", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        "sign_comp": ParagraphStyle("inv_sign_comp", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.0, leading=8.5, alignment=TA_CENTER, textColor=BLUE_PRIMARY),
    }


def _header(styles: Dict[str, ParagraphStyle], copy_label: str, doc_type: str = "INV") -> Table:
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
        Paragraph(comp_th, styles["company_th"]),
        Paragraph(comp_en, styles["company_en"]),
        Paragraph(addr_line1, styles["company_addr"]),
        Paragraph(tax_id_line, styles["company_addr"]),
        Paragraph(tel_line, styles["company_addr"]),
    ]

    title_th, title_en = DOC_TITLES.get(doc_type.upper() if doc_type else "INV", ("ใบส่งของ/ใบแจ้งหนี้", "Delivery Order/Invoice"))
    badge_label = "สำเนา/Copy" if copy_label == "copy" else "ต้นฉบับ/Original"

    right_paragraphs = [
        Paragraph(badge_label, styles["orig_copy_dark"]),
        Spacer(1, 1.5 * mm),
        Paragraph(title_th, styles["doc_title_th"]),
        Paragraph(title_en, styles["doc_title_en"]),
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


def _customer_card(invoice: Dict[str, Any], customer: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    cname = invoice.get("customer_name") or customer.get("company_name") or "RED LINE INTERNATIONAL SERVICES CO.,LIMITED"
    caddr = invoice.get("customer_address") or customer.get("address") or ""
    ctax = invoice.get("customer_tax_id") or customer.get("tax_id") or ""
    ctel = invoice.get("customer_tel") or invoice.get("tel") or customer.get("phone") or ""
    ccontact = invoice.get("contact_person") or invoice.get("attention") or customer.get("contact_person") or ""

    left_cells = [
        Paragraph("<b>ลูกค้า / Customer</b>", styles["cust_head"]),
        Paragraph(f"<b>{cname}</b>", styles["cust_name"]),
    ]
    if caddr:
        for line in str(caddr).split("\n"):
            if line.strip():
                left_cells.append(Paragraph(line.strip(), styles["cust_text"]))
    left_cells.append(Paragraph(f"เลขที่ผู้เสียภาษี {ctax}" if ctax else "เลขที่ผู้เสียภาษี", styles["cust_text"]))
    left_cells.append(Paragraph(f"โทร. {ctel}" if ctel else "โทร.", styles["cust_text"]))
    left_cells.append(Paragraph(f"ติดต่อ/ประสานงาน : {ccontact}" if ccontact else "ติดต่อ/ประสานงาน :", styles["cust_text"]))

    doc_date = _fmt_thai_date(invoice.get("issue_date") or invoice.get("doc_date") or date.today())
    due_date = _fmt_thai_date(invoice.get("due_date") or invoice.get("issue_date") or date.today())
    doc_no = str(invoice.get("doc_no") or "IV2607-0006")
    
    # Reference resolving (B/L No.)
    ref_val = invoice.get("ref_doc_no") or invoice.get("bl_no") or invoice.get("job_no") or ""
    if ref_val and not str(ref_val).upper().startswith("B/L"):
        ref_text = f"B/L : {ref_val}"
    else:
        ref_text = str(ref_val or "—")

    credit_days = invoice.get("credit_days", 0) or 0
    credit_str = f"{credit_days} วัน"
    prepared_by = str(invoice.get("prepared_by") or invoice.get("created_by") or "PATTAMA").upper()

    right_rows = [
        [Paragraph("วันที่ / Date", styles["meta_label"]), Paragraph(f": {doc_date}", styles["meta_val"])],
        [Paragraph("เลขที่ / No.", styles["meta_label"]), Paragraph(f": {doc_no}", styles["meta_val"])],
        [Paragraph("อ้างอิง / Ref.", styles["meta_label"]), Paragraph(f": {ref_text}", styles["meta_val"])],
        [Paragraph("เครดิต (วัน) / Credit", styles["meta_label"]), Paragraph(f": {credit_str}", styles["meta_val"])],
        [Paragraph("ครบกำหนด / Due Date", styles["meta_label"]), Paragraph(f": {due_date}", styles["meta_val"])],
        [Paragraph("ผู้จัดทำ / Prepared By", styles["meta_label"]), Paragraph(f": {prepared_by}", styles["meta_val"])],
    ]

    right_tbl = Table(right_rows, colWidths=[36 * mm, 46 * mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.8),
    ]))

    card = Table([[left_cells, right_tbl]], colWidths=[100 * mm, 82 * mm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, BLUE_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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

    card = Table([[left, right]], colWidths=[146 * mm, 36 * mm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, BLUE_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return card


def _items_table(items: List[Dict[str, Any]], styles: Dict[str, ParagraphStyle]) -> Table:
    headers = [
        Paragraph("<b>ลำดับ รายการ<br/>No. Description</b>", styles["th_left"]),
        "",
        Paragraph("<b>จำนวน<br/>Quantity</b>", styles["th_right"]),
        Paragraph("<b>หน่วย<br/>Unit</b>", styles["th_center"]),
        Paragraph("<b>ราคา/หน่วย<br/>Unit Price</b>", styles["th_right"]),
        Paragraph("<b>ส่วนลด %<br/>Discount</b>", styles["th_right"]),
        Paragraph("<b>จำนวนเงิน<br/>Amount</b>", styles["th_right"]),
    ]

    data = [headers]
    for i, it in enumerate(items or [], 1):
        desc = it.get("description") or "FREIGHT CHARGES"
        qty = float(it.get("quantity") or 1)
        unit = it.get("unit") or it.get("package_unit") or ""
        uprice = float(it.get("unit_price") or 0)
        disc = float(it.get("discount_percent") or it.get("discount") or 0)
        amt = float(it.get("amount") or (qty * uprice * (1 - disc / 100)))

        row = [
            Paragraph(f"{i}", styles["td_center"]),
            Paragraph(desc, styles["td_left"]),
            Paragraph(f"{qty:,.2f}", styles["td_right"]),
            Paragraph(str(unit), styles["td_center"]),
            Paragraph(f"{uprice:,.2f}", styles["td_right"]),
            Paragraph(f"{disc:,.2f}", styles["td_right"]),
            Paragraph(f"{amt:,.2f}", styles["td_right"]),
        ]
        data.append(row)

    # Pad empty rows to maintain professional layout if few items
    pad_count = max(0, 8 - len(items or []))
    for _ in range(pad_count):
        data.append([Paragraph("", styles["td_center"])] * 7)

    tbl = Table(
        data,
        colWidths=[10 * mm, 68 * mm, 18 * mm, 16 * mm, 22 * mm, 20 * mm, 28 * mm],
        repeatRows=1,
    )
    tbl.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, BLUE_BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def _totals_section(invoice: Dict[str, Any], items: List[Dict[str, Any]], styles: Dict[str, ParagraphStyle]) -> Table:
    subtotal = float(invoice.get("subtotal") or invoice.get("total_before_vat") or 0)
    vat_amt = float(invoice.get("vat_amount") or invoice.get("total_vat_7") or 0)
    total_amt = float(invoice.get("total_amount") or (subtotal + vat_amt))
    grand_total = float(invoice.get("grand_total") or invoice.get("total_amount") or total_amt)
    
    if subtotal == 0 and items:
        subtotal = sum(float(x.get("amount") or 0) for x in items)
        total_amt = subtotal + vat_amt
        grand_total = total_amt

    words = thai_baht_text(grand_total)
    words_text = f"({words})"

    remarks = invoice.get("remark") or invoice.get("remarks") or ""

    left_cells = [
        Paragraph("<b>หมายเหตุ / Remarks :</b>", styles["remark_label"]),
        Paragraph(str(remarks), styles["remark_val"]) if remarks else Paragraph("", styles["remark_val"]),
    ]

    right_rows = [
        [Paragraph("จำนวนเงินก่อนภาษี", styles["tot_label"]), Paragraph(f"{subtotal:,.2f}", styles["tot_val"])],
        [Paragraph("ภาษีมูลค่าเพิ่ม", styles["tot_label"]), Paragraph(f"{vat_amt:,.2f}", styles["tot_val"])],
        [Paragraph("จำนวนเงินรวมทั้งสิ้น", styles["tot_label"]), Paragraph(f"{total_amt:,.2f}", styles["tot_val"])],
        [Paragraph("<b>จำนวนเงินรวมสุทธิ</b>", styles["net_label"]), Paragraph(f"<b>{grand_total:,.2f}</b>", styles["net_val"])],
    ]

    right_tbl = Table(right_rows, colWidths=[42 * mm, 36 * mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
        # Highlight Net Total Row with box
        ("BOX", (0, 3), (1, 3), 0.8, BLUE_BORDER),
        ("BACKGROUND", (0, 3), (1, 3), BLUE_LIGHT),
    ]))

    top_tbl = Table([[left_cells, right_tbl]], colWidths=[104 * mm, 78 * mm])
    top_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Baht words row below
    words_p = Paragraph(f"<b>{words_text}</b>", styles["thai_words"])
    words_tbl = Table([[words_p]], colWidths=[182 * mm])
    words_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    return Table([[top_tbl], [words_tbl]], colWidths=[182 * mm], style=TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))


def _signature_block(styles: Dict[str, ParagraphStyle]) -> Table:
    box1 = [
        Spacer(1, 13 * mm),
        Paragraph("ผู้รับสินค้า / Receiver", styles["sign_role"]),
        Spacer(1, 1.5 * mm),
        Paragraph("วันที่/Date:_____/_____/_____", styles["sign_date"]),
    ]

    box2 = [
        Spacer(1, 13 * mm),
        Paragraph("ผู้ส่งสินค้า / Sender", styles["sign_role"]),
        Spacer(1, 1.5 * mm),
        Paragraph("วันที่/Date:_____/_____/_____", styles["sign_date"]),
    ]

    stamp_path = Path(BASE_DIR) / "assets" / "company_stamp_blue.png"
    if not stamp_path.exists():
        stamp_path = Path(COMPANY.get("logo_path", ""))
    
    stamp_img = None
    if stamp_path.exists():
        try:
            ir = ImageReader(str(stamp_path))
            iw, ih = ir.getSize()
            scale = min(28 * mm / iw, 13 * mm / ih)
            stamp_img = Image(str(stamp_path), width=iw * scale, height=ih * scale)
        except Exception:
            stamp_img = None

    box3 = [
        stamp_img or Spacer(1, 4 * mm),
        Spacer(1, 0.5 * mm),
        Paragraph("ผู้มีอำนาจลงนาม", styles["sign_role"]),
        Paragraph("Authorized Signature", styles["sign_role"]),
        Spacer(1, 0.8 * mm),
        Paragraph("วันที่/Date:_____/_____/_____", styles["sign_date"]),
    ]

    sig_tbl = Table([[box1, box2, box3]], colWidths=[60 * mm, 60 * mm, 62 * mm], rowHeights=[27 * mm])
    sig_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 0.6, BLUE_BORDER),
        ("BOX", (1, 0), (1, 0), 0.6, BLUE_BORDER),
        ("BOX", (2, 0), (2, 0), 0.6, BLUE_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return sig_tbl


def _build_page_story(invoice: Dict[str, Any], customer: Dict[str, Any], items: List[Dict[str, Any]], copy_label: str, styles: Dict[str, ParagraphStyle]) -> List[Any]:
    story = []
    doc_type = invoice.get("doc_type", "INV")
    story.append(_header(styles, copy_label, doc_type=doc_type))
    story.append(Spacer(1, 2.5 * mm))
    story.append(_customer_card(invoice, customer, styles))
    story.append(Spacer(1, 1.5 * mm))
    story.append(_shipping_address_card(invoice, styles))
    story.append(Spacer(1, 2.0 * mm))
    story.append(_items_table(items, styles))
    story.append(Spacer(1, 2.0 * mm))
    story.append(_totals_section(invoice, items, styles))
    story.append(Spacer(1, 3.0 * mm))
    story.append(_signature_block(styles))
    return story


def generate_invoice_pdf(
    invoice: Dict[str, Any],
    customer: Dict[str, Any] = None,
    output_path: str = None,
) -> str:
    """Generate professional 2-page Delivery Order / Invoice PDF matching company standard."""
    doc_type = invoice.get("doc_type", "INV")
    customer = customer or {}
    items = list(invoice.get("items") or [])
    doc_no = invoice.get("doc_no", "INV")

    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"INV_{doc_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"Delivery Order / Invoice {doc_no}",
        author=COMPANY.get("name", "NATTAYAARAT CO., LTD."),
    )

    styles = _styles()
    story = []

    # Page 1: Original
    story.extend(_build_page_story(invoice, customer, items, "original", styles))

    # Page 2: Copy
    story.append(PageBreak())
    story.extend(_build_page_story(invoice, customer, items, "copy", styles))

    def _draw_canvas(canvas, doc_obj):
        # Official presentation without draft watermark overlay
        pass

    doc.build(story, onFirstPage=_draw_canvas, onLaterPages=_draw_canvas)
    return output_path
