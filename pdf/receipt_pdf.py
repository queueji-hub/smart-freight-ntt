"""Receipt / Tax Invoice PDF template based on the supplied company reference.

Designed for the small-business workflow:
- Green financial-document visual language
- Original + copy pages in one PDF
- Customer/tax ID, document metadata, line items, VAT/WHT, amount in words
- Payer / Receiver / Authorized Signature blocks
"""
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD
from utils.number_to_words import thai_baht_text, number_to_english_words

GREEN = colors.HexColor("#16A34A")
GREEN_DARK = colors.HexColor("#166534")
GREEN_LIGHT = colors.HexColor("#F0FDF4")
GREEN_BORDER = colors.HexColor("#86EFAC")
TEXT = colors.HexColor("#111827")
MUTED = colors.HexColor("#475569")


def _fmt_date(value) -> str:
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d %B %Y")
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d %B %Y")
    except Exception:
        return str(value)


def _money(value) -> str:
    try:
        return f"{float(value or 0):,.2f}"
    except Exception:
        return "0.00"


def _styles():
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle("rc_company", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=14, leading=17, textColor=TEXT),
        "addr": ParagraphStyle("rc_addr", parent=base["Normal"], fontName=THAI_FONT, fontSize=8, leading=10, textColor=TEXT),
        "title": ParagraphStyle("rc_title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=14, leading=17, textColor=GREEN_DARK, alignment=TA_RIGHT),
        "small": ParagraphStyle("rc_small", parent=base["Normal"], fontName=THAI_FONT, fontSize=8, leading=10, textColor=TEXT),
        "small_bold": ParagraphStyle("rc_small_bold", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8, leading=10, textColor=TEXT),
        "header": ParagraphStyle("rc_header", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8, leading=10, textColor=TEXT),
        "right": ParagraphStyle("rc_right", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=9, leading=11, textColor=TEXT, alignment=TA_RIGHT),
        "words": ParagraphStyle("rc_words", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=10, leading=13, textColor=GREEN_DARK, alignment=TA_RIGHT),
    }


def _header(styles, copy_label: str, invoice: Dict[str, Any]):
    logo = None
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        try:
            from reportlab.lib.utils import ImageReader
            ir = ImageReader(logo_path)
            iw, ih = ir.getSize()
            scale = min(36 * mm / iw, 22 * mm / ih)
            logo = Image(logo_path, width=iw * scale, height=ih * scale)
        except Exception:
            logo = None
    if logo is None:
        logo = Paragraph("<b>NATTAYARAAT</b>", styles["company"])

    address = (
        f"<b>{COMPANY.get('name_th', COMPANY.get('name', ''))}</b><br/>"
        f"{COMPANY.get('name_en', COMPANY.get('name', ''))}<br/>"
        f"{COMPANY.get('address_line1', '')}<br/>"
        f"{COMPANY.get('address_line2', '')} {COMPANY.get('address_line3', '')}<br/>"
        f"Tax ID: {COMPANY.get('tax_id', '')} &nbsp; Tel: {COMPANY.get('tel', '')}"
    )
    doc_title = "ใบเสร็จรับเงิน/ใบกำกับภาษี"
    en_title = "Receipt / Tax Invoice"
    if copy_label == "copy":
        top_right = "<b>ไม่ใช่ใบกำกับภาษี</b><br/>สำเนา/Copy"
    else:
        top_right = "ต้นฉบับ/Original"

    right = Paragraph(f"{top_right}<br/><br/><font color='#16A34A'><b>{en_title}</b></font>", styles["title"])
    tbl = Table([[logo, Paragraph(address, styles["addr"]), right]], colWidths=[38 * mm, 89 * mm, 53 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl


def _info_card(invoice: Dict[str, Any], styles):
    left = [
        Paragraph("<b>ลูกค้า / Customer</b>", styles["small_bold"]),
        Paragraph(str(invoice.get("customer_name") or ""), styles["small_bold"]),
        Paragraph(str(invoice.get("customer_address") or ""), styles["small"]),
        Paragraph(f"เลขประจำตัวผู้เสียภาษี: {invoice.get('customer_tax_id') or '—'}", styles["small"]),
        Paragraph(f"ติดต่อ/ประสานงาน: {invoice.get('contact_person') or '—'}", styles["small"]),
    ]
    right_rows = [
        ("วันที่ / Date", _fmt_date(invoice.get("issue_date"))),
        ("เลขที่ / No.", str(invoice.get("doc_no") or "")),
        ("อ้างอิง / Ref.", str(invoice.get("ref_doc_no") or invoice.get("job_no") or "—")),
        ("เครดิต (วัน) / Credit", str(invoice.get("credit_days") or 0)),
        ("ครบกำหนด / Due Date", _fmt_date(invoice.get("due_date"))),
        ("ผู้จัดทำ / Prepared By", str(invoice.get("prepared_by") or invoice.get("created_by") or "—")),
    ]
    details = [[Paragraph(f"<b>{k}</b>", styles["small"]), Paragraph(f": {v}", styles["small"])] for k, v in right_rows]
    right_tbl = Table(details, colWidths=[40 * mm, 43 * mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    card = Table([[left, right_tbl]], colWidths=[97 * mm, 83 * mm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.9, GREEN_BORDER),
        ("ROUNDEDCORNERS", [10, 10, 10, 10]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return card


def _items_table(items: List[Dict[str, Any]], styles):
    rows = [[
        Paragraph("No.", styles["header"]),
        Paragraph("Description", styles["header"]),
        Paragraph("Quantity", styles["header"]),
        Paragraph("Unit", styles["header"]),
        Paragraph("Unit Price", styles["header"]),
        Paragraph("Discount %", styles["header"]),
        Paragraph("Amount", styles["header"]),
    ]]
    for i, item in enumerate(items or [], 1):
        qty = float(item.get("quantity") or 0)
        unit_price = float(item.get("unit_price") or 0)
        amount = float(item.get("amount") if item.get("amount") is not None else qty * unit_price)
        rows.append([
            Paragraph(str(i), styles["small"]),
            Paragraph(str(item.get("description") or ""), styles["small"]),
            Paragraph(_money(qty), styles["right"]),
            Paragraph(str(item.get("unit") or ""), styles["small"]),
            Paragraph(_money(unit_price), styles["right"]),
            Paragraph(_money(item.get("discount_pct") or 0), styles["right"]),
            Paragraph(_money(amount), styles["right"]),
        ])
    if len(rows) == 1:
        rows.append(["", Paragraph("No line items", styles["small"]), "", "", "", "", ""])
    tbl = Table(rows, colWidths=[10 * mm, 76 * mm, 20 * mm, 18 * mm, 24 * mm, 20 * mm, 22 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, GREEN),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, GREEN),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("ALIGN", (4, 1), (6, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _totals(invoice: Dict[str, Any], styles):
    cur = invoice.get("currency", "THB")
    sym = "฿ " if cur == "THB" else f"{cur} "
    summary = invoice.get("summary") or {}
    before_vat = float(summary.get("total_before_vat", invoice.get("subtotal", 0)) or 0)
    vat = float(summary.get("total_vat_7", invoice.get("vat_amount", 0)) or 0)
    wht = float(summary.get("wht_total", invoice.get("wht_amount", 0)) or 0)
    total = float(summary.get("grand_total", invoice.get("total_amount", 0)) or 0)
    rows = [
        [Paragraph("จำนวนเงินก่อนภาษี", styles["small_bold"]), Paragraph(f"{sym}{_money(before_vat)}", styles["right"])],
        [Paragraph("ภาษีมูลค่าเพิ่ม", styles["small_bold"]), Paragraph(f"{sym}{_money(vat)}", styles["right"])],
        [Paragraph("หัก ณ ที่จ่าย", styles["small_bold"]), Paragraph(f"-{sym}{_money(wht)}", styles["right"])],
        [Paragraph("จำนวนเงินรวมทั้งสิ้น", styles["small_bold"]), Paragraph(f"{sym}{_money(total)}", styles["right"])],
    ]
    tbl = Table(rows, colWidths=[60 * mm, 40 * mm])
    tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 3), (-1, 3), 1.2, GREEN),
        ("LINEBELOW", (0, 3), (-1, 3), 1.2, GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl, total, cur


def _signature(styles):
    left = [Spacer(1, 12 * mm), Paragraph("____________________________", styles["small"]), Paragraph("ผู้จ่ายเงิน / Payer", styles["small_bold"]), Paragraph("วันที่/Date:____/____/______", styles["small"])]
    mid = [Spacer(1, 12 * mm), Paragraph("____________________________", styles["small"]), Paragraph("ผู้รับเงิน / Receiver", styles["small_bold"]), Paragraph("วันที่/Date:____/____/______", styles["small"])]
    right = [Spacer(1, 7 * mm), Paragraph("____________________________", styles["small"]), Paragraph("ผู้มีอำนาจลงนาม / Authorized Signature", styles["small_bold"]), Paragraph(COMPANY.get("signer_name", ""), styles["small"]), Paragraph(COMPANY.get("signer_title", ""), styles["small"])]
    tbl = Table([[left, mid, right]], colWidths=[60 * mm, 60 * mm, 60 * mm])
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, GREEN_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, GREEN_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def generate_receipt_pdf(invoice: Dict[str, Any], customer: Dict[str, Any] = None, output_path: str = None) -> str:
    """Generate the supplied reference-style Receipt / Tax Invoice PDF."""
    data = dict(invoice or {})
    if customer:
        data.update({
            "customer_tax_id": customer.get("tax_id"),
            "customer_address": customer.get("address"),
            "contact_person": customer.get("contact_person"),
        })
    data.setdefault("doc_type", "RC")
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"RC_{data.get('doc_no', 'receipt')}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    styles = _styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=15 * mm,
        title=f"Receipt / Tax Invoice {data.get('doc_no', '')}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )

    story = []
    for copy_label in ("original", "copy"):
        story.append(_header(styles, copy_label, data))
        story.append(Spacer(1, 3 * mm))
        story.append(_info_card(data, styles))
        story.append(Spacer(1, 3 * mm))

        ship_addr = data.get("shipping_address") or data.get("customer_address") or ""
        addr_tbl = Table([[Paragraph("<b>สถานที่จัดส่ง / Shipping Address:</b>", styles["small_bold"]), Paragraph(str(ship_addr), styles["small"])]], colWidths=[50 * mm, 130 * mm])
        addr_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.9, GREEN_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(addr_tbl)
        story.append(Spacer(1, 4 * mm))
        story.append(_items_table(data.get("items", []), styles))
        story.append(Spacer(1, 6 * mm))

        totals_tbl, total, currency = _totals(data, styles)
        words = thai_baht_text(total) if currency == "THB" else number_to_english_words(total, currency)
        words_tbl = Table([[Paragraph("จำนวนเงินรวมสุทธิ", styles["small_bold"]), Paragraph(words, styles["words"])]], colWidths=[55 * mm, 125 * mm])
        words_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.8, GREEN),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        totals_wrap = Table([[Paragraph("", styles["small"]), totals_tbl]], colWidths=[80 * mm, 100 * mm])
        totals_wrap.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(words_tbl)
        story.append(totals_wrap)
        story.append(Spacer(1, 4 * mm))
        if data.get("remark"):
            story.append(Paragraph(f"<b>หมายเหตุ / Remarks:</b> {data.get('remark')}", styles["small"]))
        story.append(Spacer(1, 12 * mm))
        story.append(_signature(styles))
        if copy_label == "original":
            story.append(PageBreak())

    def _footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(GREEN_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, 10 * mm, A4[0] - 15 * mm, 10 * mm)
        canvas.setFont(THAI_FONT, 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(15 * mm, 6 * mm, COMPANY.get("name", "NATTAYARAAT CO., LTD."))
        canvas.drawRightString(A4[0] - 15 * mm, 6 * mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output_path
