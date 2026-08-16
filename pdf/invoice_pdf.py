"""A4 Finance document generator: Tax Invoice / Receipt / Billing Note / CN / DN / SOA.

Phase 30 finance standard:
- clean A4 layout based on the supplied NATTAYARAAT reference documents
- explicit seller/buyer identity, tax IDs, dates, references and amounts
- VAT/WHT visibility and amount-in-words
- Original/Copy pair for TAX INVOICE / RECEIPT
- Draft/Pending Approval watermark; Approved renders clean
- backward-compatible generator signature
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

BRAND_BLUE = colors.HexColor("#1F4E9E")
BRAND_GREEN = colors.HexColor("#16A34A")
HEADER_GREY = colors.HexColor("#E5E7EB")
LIGHT_BLUE = colors.HexColor("#F5F8FF")
LIGHT_GREEN = colors.HexColor("#F0FDF4")
BORDER = colors.HexColor("#CBD5E1")

DOC_TITLES = {
    "INV": ("ใบเสร็จรับเงิน / ใบกำกับภาษี", "Receipt / Tax Invoice"),
    "BN": ("ใบวางบิล", "Billing Note"),
    "CN": ("ใบลดหนี้", "Credit Note"),
    "DN": ("ใบเพิ่มหนี้", "Debit Note"),
    "SOA": ("ใบแจ้งยอดบัญชี", "Statement of Account"),
}


def _fmt(d) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%Y")
        except Exception:
            return d
    try:
        return d.strftime("%d-%b-%Y")
    except Exception:
        return str(d)


def _money(n) -> str:
    try:
        return f"{float(n or 0):,.2f}"
    except Exception:
        return "0.00"


def _safe(value, default="—") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if not text or text.lower() in {"none", "nan", "nat"} else text


def _accent(doc_type: str):
    return BRAND_GREEN if doc_type == "INV" else BRAND_BLUE


def _styles(accent):
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle(
            "finance_company", parent=base["Normal"], fontName=THAI_FONT_BOLD,
            fontSize=17, textColor=accent, leading=21, spaceAfter=5,
        ),
        "addr": ParagraphStyle(
            "finance_addr", parent=base["Normal"], fontName=THAI_FONT,
            fontSize=8.5, textColor=BRAND_BLUE, leading=12,
        ),
        "title_th": ParagraphStyle(
            "finance_title_th", parent=base["Normal"], fontName=THAI_FONT_BOLD,
            fontSize=15, textColor=accent, alignment=TA_RIGHT, leading=18,
        ),
        "title_en": ParagraphStyle(
            "finance_title_en", parent=base["Normal"], fontName=THAI_FONT,
            fontSize=9, textColor=accent, alignment=TA_RIGHT, leading=12,
        ),
        "label": ParagraphStyle(
            "finance_label", parent=base["Normal"], fontName=THAI_FONT_BOLD,
            fontSize=8.5, leading=11,
        ),
        "value": ParagraphStyle(
            "finance_value", parent=base["Normal"], fontName=THAI_FONT,
            fontSize=8.5, leading=11,
        ),
        "value_bold": ParagraphStyle(
            "finance_value_bold", parent=base["Normal"], fontName=THAI_FONT_BOLD,
            fontSize=9, leading=11,
        ),
        "right": ParagraphStyle(
            "finance_right", parent=base["Normal"], fontName=THAI_FONT,
            fontSize=8.5, alignment=TA_RIGHT, leading=11,
        ),
        "center": ParagraphStyle(
            "finance_center", parent=base["Normal"], fontName=THAI_FONT,
            fontSize=8.5, alignment=TA_CENTER, leading=11,
        ),
        "small": ParagraphStyle(
            "finance_small", parent=base["Normal"], fontName=THAI_FONT,
            fontSize=7.5, leading=10,
        ),
    }


def _header(styles, accent):
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(logo_path)
        iw, ih = ir.getSize()
        scale = min(42 * mm / iw, 25 * mm / ih)
        logo = Image(logo_path, width=iw * scale, height=ih * scale)
    else:
        logo = Paragraph("[LOGO]", styles["value"])

    company_addr = (
        f'<b>{COMPANY.get("name_th", "")}</b><br/>'
        f'{COMPANY.get("address_line1", "")}<br/>'
        f'{COMPANY.get("address_line2", "")} {COMPANY.get("address_line3", "")}<br/>'
        f'<b>Tax ID: {COMPANY.get("tax_id", "—")}</b> ({COMPANY.get("branch_th", "สำนักงานใหญ่")}) · '
        f'Tel: {COMPANY.get("tel", "—")}<br/>'
        f'{COMPANY.get("email", "—")} · {COMPANY.get("website", "—")}'
    )
    company_block = [
        Paragraph(COMPANY["name_en"], styles["company"]),
        Paragraph(company_addr, styles["addr"]),
    ]

    tbl = Table([[logo, company_block]], colWidths=[44 * mm, 86 * mm, 50 * mm])
    # Add an empty right cell here so the caller can keep the title separate.
    tbl = Table([[logo, company_block]], colWidths=[44 * mm, 86 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl


def _title_block(invoice, styles, accent, copy_label):
    doc_type = invoice.get("doc_type", "INV")
    title_th, title_en = DOC_TITLES.get(doc_type, (doc_type, doc_type))
    status = str(invoice.get("approval_status") or invoice.get("status") or "Draft").strip()
    status_html = ""
    if status:
        status_color = BRAND_GREEN if status.lower() == "approved" else colors.HexColor("#B45309")
        status_html = f'<font color="{status_color.hexval()}"><b>{status}</b></font>'

    right = [
        Paragraph(title_th, styles["title_th"]),
        Paragraph(title_en, styles["title_en"]),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>{copy_label}</b>", styles["title_en"]),
        Paragraph(status_html, styles["title_en"]),
    ]
    return Table([["", right]], colWidths=[130 * mm, 50 * mm], style=TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))


def _info_block(invoice, customer, styles, accent):
    customer = customer or {}
    customer_name = invoice.get("customer_name") or customer.get("company_name")
    customer_address = invoice.get("customer_address") or customer.get("address")
    customer_tax_id = invoice.get("customer_tax_id") or customer.get("tax_id")
    buyer_branch = invoice.get("buyer_branch") or customer.get("branch_name")
    seller_branch = invoice.get("seller_branch") or COMPANY.get("branch_name")

    bill_rows = [
        ("Customer", _safe(customer_name)),
        ("Address", _safe(customer_address)),
        ("Tax ID", _safe(customer_tax_id)),
    ]
    if buyer_branch:
        bill_rows.append(("Branch", buyer_branch))

    details_rows = [
        ("Document No.", _safe(invoice.get("doc_no"), "")),
        ("Issue Date", _fmt(invoice.get("issue_date"))),
        ("Due Date", _fmt(invoice.get("due_date"))),
        ("Reference", _safe(invoice.get("ref_doc_no") or invoice.get("job_no"))),
        ("Currency", _safe(invoice.get("currency"), "THB")),
        ("Prepared By", _safe(invoice.get("created_by"))),
    ]
    if seller_branch:
        details_rows.append(("Seller Branch", seller_branch))

    left = [[Paragraph("<b>BILL TO / CUSTOMER</b>", styles["label"]), ""]]
    for label, value in bill_rows:
        left.append([Paragraph(f"<b>{label}</b>", styles["label"]), Paragraph(value, styles["value"])])
    left_tbl = Table(left, colWidths=[28 * mm, 66 * mm])
    left_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("SPAN", (0, 0), (-1, 0)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOX", (0, 0), (-1, -1), 0.6, accent),
    ]))

    right = [[Paragraph("<b>DOCUMENT DETAILS</b>", styles["label"]), ""]]
    for label, value in details_rows:
        right.append([Paragraph(f"<b>{label}</b>", styles["label"]), Paragraph(value, styles["value"])])
    right_tbl = Table(right, colWidths=[34 * mm, 46 * mm])
    right_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("SPAN", (0, 0), (-1, 0)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOX", (0, 0), (-1, -1), 0.6, accent),
    ]))

    return Table([[left_tbl, right_tbl]], colWidths=[96 * mm, 84 * mm], style=TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))


def _shipping_block(invoice, styles, accent):
    address = invoice.get("shipping_address") or invoice.get("delivery_address")
    if not address:
        return None
    tbl = Table([[Paragraph("<b>SHIPPING / DELIVERY ADDRESS</b>", styles["label"])],
                 [Paragraph(str(address), styles["value"])]], colWidths=[180 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), accent),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _items_table(items: List[Dict[str, Any]], styles, accent):
    data = [[
        Paragraph("<b>NO.</b>", styles["center"]),
        Paragraph("<b>DESCRIPTION</b>", styles["label"]),
        Paragraph("<b>QTY</b>", styles["center"]),
        Paragraph("<b>UNIT</b>", styles["center"]),
        Paragraph("<b>UNIT PRICE</b>", styles["right"]),
        Paragraph("<b>DISCOUNT</b>", styles["right"]),
        Paragraph("<b>VAT</b>", styles["center"]),
        Paragraph("<b>WHT</b>", styles["center"]),
        Paragraph("<b>AMOUNT</b>", styles["right"]),
    ]]
    for i, item in enumerate(items or [], 1):
        tax = item.get("tax_type", "VAT 7%")
        wht = item.get("wht_type", "None")
        discount = item.get("discount", 0) or 0
        unit = item.get("unit") or item.get("package_unit") or ""
        data.append([
            Paragraph(str(i), styles["center"]),
            Paragraph(_safe(item.get("description"), ""), styles["value"]),
            Paragraph(_money(item.get("quantity")), styles["right"]),
            Paragraph(_safe(unit, ""), styles["center"]),
            Paragraph(_money(item.get("unit_price")), styles["right"]),
            Paragraph(_money(discount), styles["right"]),
            Paragraph({"VAT 7%": "7%", "Non-VAT": "-", "Advance": "ADV"}.get(tax, tax), styles["center"]),
            Paragraph({"None": "-", "WHT 1%": "1%", "WHT 3%": "3%"}.get(wht, wht), styles["center"]),
            Paragraph(_money(item.get("amount")), styles["right"]),
        ])
    tbl = Table(data, colWidths=[8*mm, 56*mm, 15*mm, 15*mm, 22*mm, 18*mm, 12*mm, 12*mm, 22*mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (5, -1), "RIGHT"),
        ("ALIGN", (6, 1), (7, -1), "CENTER"),
        ("ALIGN", (8, 1), (8, -1), "RIGHT"),
    ]))
    return tbl


def _totals_block(invoice, styles, accent):
    cur = invoice.get("currency", "THB")
    sym = "฿" if cur == "THB" else f"{cur} "
    summary = dict(invoice.get("summary") or {})
    summary.setdefault("total_before_vat", invoice.get("subtotal", 0) or 0)
    summary.setdefault("total_vat_7", invoice.get("vat_amount", 0) or 0)
    summary.setdefault("total_advance", invoice.get("advance_amount", 0) or 0)
    summary.setdefault("wht_1_amount", invoice.get("wht_1_amount", 0) or 0)
    summary.setdefault("wht_3_amount", invoice.get("wht_3_amount", 0) or 0)
    summary.setdefault("grand_total", invoice.get("total_amount", 0) or 0)
    summary["total_before_wht"] = summary.get("total_before_wht") or (
        float(summary["total_before_vat"]) + float(summary["total_vat_7"]) + float(summary["total_advance"])
    )

    rows = [
        ["Subtotal", f"{sym}{_money(summary['total_before_vat'])}"],
        ["VAT 7%", f"{sym}{_money(summary['total_vat_7'])}"],
    ]
    if float(summary.get("total_advance", 0) or 0) > 0:
        rows.append(["Advance", f"{sym}{_money(summary['total_advance'])}"])
    rows.append(["Total Before WHT", f"{sym}{_money(summary['total_before_wht'])}"])
    if float(summary.get("wht_1_amount", 0) or 0) > 0:
        rows.append(["WHT 1%", f"-{sym}{_money(summary['wht_1_amount'])}"])
    if float(summary.get("wht_3_amount", 0) or 0) > 0:
        rows.append(["WHT 3%", f"-{sym}{_money(summary['wht_3_amount'])}"])
    rows.append(["GRAND TOTAL", f"{sym}{_money(summary['grand_total'])}"])
    if float(invoice.get("paid_amount", 0) or 0) > 0:
        rows.append(["Paid", f"{sym}{_money(invoice.get('paid_amount'))}"])
        rows.append(["Outstanding", f"{sym}{_money(invoice.get('outstanding'))}"])

    data = [[Paragraph(r[0], styles["value_bold"] if r[0] == "GRAND TOTAL" else styles["value"]), Paragraph(r[1], styles["right"])] for r in rows]
    grand_idx = next((i for i, r in enumerate(rows) if r[0] == "GRAND TOTAL"), -1)
    tbl = Table(data, colWidths=[58*mm, 42*mm])
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if grand_idx >= 0:
        cmds += [
            ("BACKGROUND", (0, grand_idx), (-1, grand_idx), accent),
            ("TEXTCOLOR", (0, grand_idx), (-1, grand_idx), colors.white),
            ("LINEABOVE", (0, grand_idx), (-1, grand_idx), 1, accent),
        ]
    tbl.setStyle(TableStyle(cmds))
    return tbl


def _preflight(invoice, customer):
    """Return human-readable blockers for issuing an official Thai tax invoice."""
    blockers = []
    doc_type = str(invoice.get("doc_type") or "INV").upper()
    approval = str(invoice.get("approval_status") or invoice.get("status") or "Draft").strip().lower()
    customer = customer or {}
    if doc_type != "INV" or approval != "approved":
        return blockers

    if not COMPANY.get("tax_id"):
        blockers.append("Seller Tax ID is missing from company configuration.")
    if not (invoice.get("customer_name") or customer.get("company_name")):
        blockers.append("Customer name is required.")
    if not (invoice.get("customer_address") or customer.get("address")):
        blockers.append("Customer address is required.")
    if not (invoice.get("customer_tax_id") or customer.get("tax_id")):
        blockers.append("Customer Tax ID is required for an official full tax invoice when applicable.")
    return blockers


def _amount_words(invoice):
    from utils.number_to_words import thai_baht_text, number_to_english_words
    total = float(invoice.get("total_amount", 0) or 0)
    currency = invoice.get("currency", "THB")
    return thai_baht_text(total) if currency == "THB" else number_to_english_words(total, currency)


def _build_page(invoice, customer, copy_label: str):
    doc_type = invoice.get("doc_type", "INV")
    accent = _accent(doc_type)
    styles = _styles(accent)
    story = []

    # Header and title
    header = _header(styles, accent)
    title = _title_block(invoice, styles, accent, copy_label)
    story.append(Table([[header, title]], colWidths=[130*mm, 50*mm], style=TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ])))
    story.append(Spacer(1, 3*mm))

    story.append(_info_block(invoice, customer, styles, accent))
    shipping = _shipping_block(invoice, styles, accent)
    if shipping:
        story.append(Spacer(1, 3*mm))
        story.append(shipping)

    story.append(Spacer(1, 4*mm))
    story.append(_items_table(invoice.get("items", []), styles, accent))
    story.append(Spacer(1, 4*mm))

    amount_words = _amount_words(invoice)
    words = Table([[Paragraph(f"<b>AMOUNT IN WORDS</b><br/>{amount_words}", styles["value"])]], colWidths=[80*mm])
    words.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREEN if doc_type == "INV" else LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    totals = _totals_block(invoice, styles, accent)
    story.append(Table([[words, totals]], colWidths=[80*mm, 100*mm], style=TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ])))

    if invoice.get("remark"):
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(f"<b>Remarks:</b> {_safe(invoice.get('remark'), '')}", styles["value"]))

    story.append(Spacer(1, 8*mm))
    signature = Table([[
        [Paragraph("Payer / Receiver", styles["center"]), Spacer(1, 10*mm), Paragraph("____________________________", styles["center"]), Paragraph("Date: ____ / ____ / ______", styles["small"])],
        [Paragraph("Customer / Received by", styles["center"]), Spacer(1, 10*mm), Paragraph("____________________________", styles["center"]), Paragraph("Date: ____ / ____ / ______", styles["small"])],
        [Paragraph("Authorized Signature", styles["center"]), Spacer(1, 10*mm), Paragraph("____________________________", styles["center"]), Paragraph(f"<b>{COMPANY['signer_name']}</b><br/>{COMPANY['signer_title']}", styles["small"])],
    ]], colWidths=[60*mm, 60*mm, 60*mm])
    signature.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, accent),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(signature)
    return story, accent


def generate_invoice_pdf(
    invoice: Dict[str, Any],
    customer: Dict[str, Any] = None,
    output_path: str = None,
) -> str:
    """Generate finance PDF while preserving the existing caller signature."""
    doc_type = invoice.get("doc_type", "INV")
    customer = customer or {}
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"{doc_type}_{invoice.get('doc_no', 'doc')}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    blockers = _preflight(invoice, customer)
    if blockers:
        raise ValueError("Official Tax Invoice preflight failed: " + " | ".join(blockers))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title=f"{DOC_TITLES.get(doc_type, (doc_type, doc_type))[0]} {invoice.get('doc_no', '')}",
        author=COMPANY["name"],
    )

    story, accent = _build_page(invoice, customer, "ต้นฉบับ / Original" if doc_type == "INV" else "Original")
    if doc_type == "INV":
        story.append(PageBreak())
        copy_story, _ = _build_page(invoice, customer, "สำเนา / Copy")
        story.extend(copy_story)

    approval = str(invoice.get("approval_status") or invoice.get("status") or "Draft").strip().lower()
    is_draft = approval in {"draft", "pending approval", "pending", "pending_approval"}

    def _draw_canvas(canvas, doc_obj):
        canvas.saveState()
        if is_draft:
            canvas.setFont(THAI_FONT_BOLD, 58)
            canvas.setFillColor(colors.Color(0.75, 0.10, 0.10, alpha=0.16))
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(32)
            canvas.drawCentredString(0, 0, "DRAFT")
            canvas.restoreState()
            canvas.saveState()
        canvas.setFont(THAI_FONT, 7.5)
        canvas.setFillColor(colors.grey)
        canvas.drawString(15 * mm, 7 * mm, "NATTAYARAAT CO., LTD.")
        canvas.drawRightString(A4[0] - 15 * mm, 7 * mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_canvas, onLaterPages=_draw_canvas)
    return output_path
