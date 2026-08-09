"""A4 Tax Invoice / Receipt / CN / DN / Billing Note PDF generator."""
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any, List

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
HEADER_GREY = colors.HexColor("#9CA3AF")

DOC_TITLES = {
    "INV": "TAX INVOICE / RECEIPT",
    "BN": "BILLING NOTE",
    "CN": "CREDIT NOTE",
    "DN": "DEBIT NOTE",
    "SOA": "STATEMENT OF ACCOUNT",
}


def _fmt(d) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%Y")
        except Exception:
            return d
    return d.strftime("%d-%b-%Y")


def _money(n) -> str:
    try:
        return f"{float(n or 0):,.2f}"
    except Exception:
        return "0.00"


def _styles():
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle("c", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=17, textColor=BRAND_GOLD,
            spaceAfter=10, leading=21),
        "addr": ParagraphStyle("a", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, textColor=BRAND_BLUE,
            leading=13, spaceBefore=4),
        "title": ParagraphStyle("t", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=18, textColor=BRAND_BLUE,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=8),
        "label": ParagraphStyle("l", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=9),
        "value": ParagraphStyle("v", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9),
        "body": ParagraphStyle("b", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, leading=12),
        "right": ParagraphStyle("r", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=9, alignment=TA_RIGHT),
    }


def _header(styles):
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(logo_path)
        iw, ih = ir.getSize()
        scale = min(40*mm / iw, 24*mm / ih)
        logo = Image(logo_path, width=iw*scale, height=ih*scale)
    else:
        logo = Paragraph("[LOGO]", styles["body"])
    
    addr = (f'<font color="#1F4E9E" size="9">'
            f'{COMPANY["address_line1"]}<br/>'
            f'{COMPANY["address_line2"]} {COMPANY["address_line3"]}<br/>'
            f'Tax ID: {COMPANY["tax_id"]} · Tel: {COMPANY["tel"]}<br/>'
            f'Email: {COMPANY["email"]}'
            f'</font>')
    
    company_block = [
        Paragraph(COMPANY["name"], styles["company"]),
        Spacer(1, 3*mm),
        Paragraph(addr, styles["addr"]),
    ]
    
    tbl = Table([[logo, company_block]], colWidths=[40*mm, 140*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return tbl


def _info_block(invoice, styles):
    """Two-column info: bill-to + invoice details."""
    bill_to = [
        Paragraph("<b>BILL TO:</b>", styles["label"]),
        Paragraph(f"<b>{invoice.get('customer_name','')}</b>", styles["value"]),
        Paragraph(f"Tax ID: {invoice.get('customer_tax_id','—')}",
                  styles["value"]),
        Paragraph(f"Address: {invoice.get('customer_address','—')}",
                  styles["value"]),
    ]
    
    details = [
        [Paragraph("<b>Document No.</b>", styles["label"]),
         Paragraph(invoice.get("doc_no", ""), styles["value"])],
        [Paragraph("<b>Issue Date</b>", styles["label"]),
         Paragraph(_fmt(invoice.get("issue_date")), styles["value"])],
        [Paragraph("<b>Due Date</b>", styles["label"]),
         Paragraph(_fmt(invoice.get("due_date")), styles["value"])],
        [Paragraph("<b>Reference</b>", styles["label"]),
         Paragraph(invoice.get("ref_doc_no") or invoice.get("job_no", "—"),
                   styles["value"])],
        [Paragraph("<b>Currency</b>", styles["label"]),
         Paragraph(invoice.get("currency", "THB"), styles["value"])],
    ]
    details_tbl = Table(details, colWidths=[35*mm, 50*mm])
    details_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 2),
    ]))
    
    tbl = Table([[bill_to, details_tbl]], colWidths=[95*mm, 85*mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return tbl


def _items_table(items: List[Dict[str, Any]], currency, styles):
    sym = "฿" if currency == "THB" else (currency + " ")
    
    data = [[
        Paragraph("<b>NO.</b>", styles["label"]),
        Paragraph("<b>DESCRIPTION</b>", styles["label"]),
        Paragraph("<b>QTY</b>", styles["label"]),
        Paragraph("<b>UNIT PRICE</b>", styles["label"]),
        Paragraph("<b>VAT</b>", styles["label"]),
        Paragraph("<b>WHT</b>", styles["label"]),
        Paragraph("<b>AMOUNT</b>", styles["label"]),
    ]]
    
    for i, item in enumerate(items, 1):
        # Shorten tax/wht labels for table
        tax = item.get("tax_type", "VAT 7%")
        tax_short = {"VAT 7%": "7%", "Non-VAT": "—", "Advance": "ADV"}.get(tax, tax)
        wht = item.get("wht_type", "None")
        wht_short = {"None": "—", "WHT 1%": "1%", "WHT 3%": "3%"}.get(wht, wht)
        
        data.append([
            Paragraph(str(i), styles["value"]),
            Paragraph(item.get("description", ""), styles["value"]),
            Paragraph(_money(item.get("quantity", 0)), styles["right"]),
            Paragraph(_money(item.get("unit_price", 0)), styles["right"]),
            Paragraph(tax_short, styles["value"]),
            Paragraph(wht_short, styles["value"]),
            Paragraph(_money(item.get("amount", 0)), styles["right"]),
        ])
    
    tbl = Table(data, colWidths=[10*mm, 70*mm, 18*mm, 25*mm, 14*mm, 13*mm, 30*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BRAND_BLUE),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("ALIGN", (2,1), (3,-1), "RIGHT"),
        ("ALIGN", (4,1), (5,-1), "CENTER"),
        ("ALIGN", (6,1), (6,-1), "RIGHT"),
        ("ALIGN", (0,1), (0,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.grey),
    ]))
    return tbl


def _totals_block(invoice, styles):
    cur = invoice.get("currency", "THB")
    sym = "฿" if cur == "THB" else (cur + " ")
    
    # Use the recomputed summary if available, otherwise build from old fields
    summary = invoice.get("summary") or {
        "total_before_vat": invoice.get("subtotal", 0) or 0,
        "total_vat_7": invoice.get("vat_amount", 0) or 0,
        "total_advance": invoice.get("advance_amount", 0) or 0,
        "wht_1_amount": invoice.get("wht_1_amount", 0) or 0,
        "wht_3_amount": invoice.get("wht_3_amount", 0) or 0,
        "grand_total": invoice.get("total_amount", 0) or 0,
    }
    summary["total_before_wht"] = summary.get("total_before_wht",
        summary["total_before_vat"] + summary["total_vat_7"] + summary["total_advance"])
    
    rows = [
        ["1. Total Before VAT",
         f"{sym}{_money(summary['total_before_vat'])}"],
        ["2. Total VAT 7%",
         f"{sym}{_money(summary['total_vat_7'])}"],
    ]
    
    if summary.get("total_advance", 0) > 0:
        rows.append(["3. Total Advance (เงินทดรองจ่าย)",
                     f"{sym}{_money(summary['total_advance'])}"])
    
    rows.append(["4. Total Before WHT",
                 f"{sym}{_money(summary['total_before_wht'])}"])
    
    if summary.get("wht_1_amount", 0) > 0:
        rows.append(["5. WHT 1%",
                     f"-{sym}{_money(summary['wht_1_amount'])}"])
    if summary.get("wht_3_amount", 0) > 0:
        rows.append(["6. WHT 3%",
                     f"-{sym}{_money(summary['wht_3_amount'])}"])
    
    rows.append(["", ""])
    rows.append(["GRAND TOTAL",
                 f"{sym}{_money(summary.get('grand_total', invoice.get('total_amount',0)))}"])
    
    if (invoice.get("paid_amount") or 0) > 0:
        rows.append(["Paid", f"{sym}{_money(invoice.get('paid_amount', 0))}"])
        rows.append(["Outstanding",
                     f"{sym}{_money(invoice.get('outstanding', 0))}"])
    
    data = [[Paragraph(r[0], styles["body"]),
             Paragraph(r[1], styles["right"])] for r in rows]
    
    tbl = Table(data, colWidths=[60*mm, 40*mm])
    
    # Find index of "GRAND TOTAL" row to highlight
    grand_idx = next((i for i, r in enumerate(rows) if r[0] == "GRAND TOTAL"), -1)
    
    style_cmds = [
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]
    if grand_idx >= 0:
        style_cmds += [
            ("BACKGROUND", (0, grand_idx), (-1, grand_idx), BRAND_BLUE),
            ("TEXTCOLOR", (0, grand_idx), (-1, grand_idx), colors.white),
            ("FONTNAME", (0, grand_idx), (-1, grand_idx), THAI_FONT_BOLD),
            ("LINEABOVE", (0, grand_idx), (-1, grand_idx), 1, colors.black),
        ]
    
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def generate_invoice_pdf(invoice: Dict[str, Any],
                          customer: Dict[str, Any] = None,
                          output_path: str = None) -> str:
    """Generate invoice/CN/DN/BN PDF."""
    doc_type = invoice.get("doc_type", "INV")
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) /
                           f"{doc_type}_{invoice.get('doc_no','doc')}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Merge customer info into invoice for display
    if customer:
        invoice = {
            **invoice,
            "customer_tax_id": customer.get("tax_id"),
            "customer_address": customer.get("address"),
        }
    
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm,
        title=f"{DOC_TITLES.get(doc_type, doc_type)} {invoice.get('doc_no','')}",
        author=COMPANY["name"],
    )
    styles = _styles()
    story = []
    
    story.append(_header(styles))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(DOC_TITLES.get(doc_type, doc_type), styles["title"]))
    story.append(_info_block(invoice, styles))
    story.append(Spacer(1, 6*mm))
    story.append(_items_table(invoice.get("items", []),
                                invoice.get("currency", "THB"), styles))
    story.append(Spacer(1, 4*mm))
    
    # Amount in Words Block
    from utils.number_to_words import thai_baht_text, number_to_english_words
    total_val = float(invoice.get("total_amount", 0) or 0)
    cur = invoice.get("currency", "THB")
    
    amount_words_text = thai_baht_text(total_val) if cur == "THB" else number_to_english_words(total_val, cur)
    
    words_table = Table([[
        Paragraph(f"<b>AMOUNT IN WORDS:</b> <font color='#1F4E9E'><b>{amount_words_text}</b></font>", styles["body"])
    ]], colWidths=[180*mm])
    words_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    
    # Right-align totals block
    totals_wrap = Table([[words_table, _totals_block(invoice, styles)]],
                         colWidths=[80*mm, 100*mm])
    totals_wrap.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(totals_wrap)
    
    if invoice.get("remark"):
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"<b>Remark:</b> {invoice.get('remark','')}",
                                styles["body"]))
    
    # Signature block
    story.append(Spacer(1, 12*mm))
    sig = Table([[
        [Paragraph("Authorized by:", styles["body"]),
         Spacer(1, 14*mm),
         Paragraph("_" * 30, styles["body"]),
         Paragraph(f"<b>{COMPANY['signer_name']}</b>", styles["body"]),
         Paragraph(COMPANY["signer_title"], styles["body"])],
        [Paragraph("Received by:", styles["body"]),
         Spacer(1, 14*mm),
         Paragraph("_" * 30, styles["body"]),
         Paragraph("Customer Signature", styles["body"]),
         Paragraph("Date: ____________", styles["body"])],
    ]], colWidths=[90*mm, 90*mm])
    sig.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(sig)
    
    is_draft = str(invoice.get("payment_status", invoice.get("status", ""))).upper().strip() != "ISSUED"

    def _draw_invoice_canvas(canvas, doc):
        canvas.saveState()
        if is_draft:
            canvas.setFont(THAI_FONT_BOLD, 64)
            canvas.setFillColor(colors.HexColor("#EF4444"), alpha=0.20)
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, "DRAFT — UNOFFICIAL COPY")

        canvas.setFont(THAI_FONT, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(15 * mm, 10 * mm, "Smart Freight NTT, — Enterprise Tax Invoice Engine")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=_draw_invoice_canvas,
        onLaterPages=_draw_invoice_canvas
    )
    return output_path
