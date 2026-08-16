"""Pure company-issued Bill of Lading renderer.

Layout is based on the supplied NATTAYARAAT B/L reference: company header,
B/L number, parties, routing/vessel, cargo grid, freight/terms, originals,
and issuance/signature. The renderer consumes a validated payload and never
queries the database.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.utils import ImageReader

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import register_thai_fonts

FONT, FONT_BOLD = register_thai_fonts()
BRAND_BLUE = colors.HexColor("#1F4E9E")
BORDER = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F3F4F6")
TEXT = colors.HexColor("#111827")
DRAFT = colors.HexColor("#B91C1C")

TOTAL_W = 190 * mm


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "nan", "nat"} else text


def _date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%b-%Y")
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d-%b-%Y")
    except Exception:
        return _s(value)


def _num(value: Any, precision: int = 2) -> str:
    try:
        n = float(value or 0)
        return "" if n == 0 else f"{n:,.{precision}f}"
    except (TypeError, ValueError):
        return ""


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle("bl_company", parent=base["Normal"], fontName=FONT_BOLD, fontSize=13, leading=15, textColor=BRAND_BLUE),
        "company_small": ParagraphStyle("bl_company_small", parent=base["Normal"], fontName=FONT, fontSize=7, leading=9, textColor=TEXT),
        "title": ParagraphStyle("bl_title", parent=base["Normal"], fontName=FONT_BOLD, fontSize=17, leading=19, alignment=TA_RIGHT, textColor=BRAND_BLUE),
        "number": ParagraphStyle("bl_number", parent=base["Normal"], fontName=FONT_BOLD, fontSize=10, leading=12, alignment=TA_RIGHT, textColor=TEXT),
        "label": ParagraphStyle("bl_label", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.8, leading=8, textColor=TEXT),
        "value": ParagraphStyle("bl_value", parent=base["Normal"], fontName=FONT, fontSize=7.2, leading=9, textColor=TEXT),
        "tiny": ParagraphStyle("bl_tiny", parent=base["Normal"], fontName=FONT, fontSize=6.2, leading=7.4, textColor=TEXT),
        "head": ParagraphStyle("bl_head", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.4, leading=7.4, alignment=TA_CENTER, textColor=TEXT),
        "center": ParagraphStyle("bl_center", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7, leading=8, alignment=TA_CENTER, textColor=TEXT),
        "terms": ParagraphStyle("bl_terms", parent=base["Normal"], fontName=FONT, fontSize=6.15, leading=7.25, textColor=TEXT),
        "status": ParagraphStyle("bl_status", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.white),
        "signature": ParagraphStyle("bl_signature", parent=base["Normal"], fontName=FONT, fontSize=6.8, leading=8, alignment=TA_CENTER, textColor=TEXT),
        "right": ParagraphStyle("bl_right", parent=base["Normal"], fontName=FONT, fontSize=7.2, leading=9, alignment=TA_RIGHT, textColor=TEXT),
    }


def _field(label: str, value: Any, styles: Dict[str, ParagraphStyle], *, tiny: bool = False) -> Paragraph:
    style = styles["tiny"] if tiny else styles["value"]
    return Paragraph(f"<b>{label}</b><br/>{_s(value)}", style)


def _company_header(styles: Dict[str, ParagraphStyle], bl_no: str) -> Table:
    logo_path = COMPANY.get("logo_path")
    logo = None
    if logo_path and Path(str(logo_path)).exists():
        ir = ImageReader(str(logo_path))
        iw, ih = ir.getSize()
        scale = min(28 * mm / iw, 20 * mm / ih)
        logo = Image(str(logo_path), width=iw * scale, height=ih * scale)
    else:
        logo = Paragraph("", styles["company_small"])

    address = (
        f"<b>{COMPANY.get('name_th', COMPANY.get('name', 'NATTAYARAAT CO., LTD.'))}</b><br/>"
        f"{_s(COMPANY.get('address_line1'))}<br/>"
        f"{_s(COMPANY.get('address_line2'))} {_s(COMPANY.get('address_line3'))}<br/>"
        f"Tax ID: {_s(COMPANY.get('tax_id'))} · Tel: {_s(COMPANY.get('tel'))}<br/>"
        f"{_s(COMPANY.get('email'))}"
    )
    company = [
        Paragraph(_s(COMPANY.get("name_en"), "NATTAYARAAT CO., LTD."), styles["company"]),
        Paragraph(address, styles["company_small"]),
    ]
    right = [Paragraph("BILL OF LADING", styles["title"]), Spacer(1, 1.5 * mm), Paragraph(f"B/L No. <b>{bl_no}</b>", styles["number"])]
    table = Table([[logo, company, right]], colWidths=[30 * mm, 92 * mm, 68 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _boxed(table_data, widths, *, header_rows=0, background=None, padding=3) -> Table:
    tbl = Table(table_data, colWidths=widths, repeatRows=header_rows or None)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    if header_rows:
        commands.append(("BACKGROUND", (0, 0), (-1, header_rows - 1), LIGHT))
    if background:
        commands.append(("BACKGROUND", (0, 0), (-1, -1), background))
    tbl.setStyle(TableStyle(commands))
    return tbl


def generate_company_bl_pdf(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    if not isinstance(payload, dict) or "bl" not in payload:
        raise ValueError("B/L PDF requires a validated payload dict with a 'bl' record.")

    bl = dict(payload.get("bl") or {})
    job = dict(payload.get("job") or {})
    containers = list(payload.get("containers") or [])
    styles = _styles()

    bl_no = _s(bl.get("bl_no"), "DRAFT")
    status = _s(bl.get("approval_status"), "Draft")

    shipper = _s(bl.get("shipper"))
    consignee = _s(bl.get("consignee"))
    notify = _s(bl.get("notify_party"), "SAME AS CONSIGNEE")
    delivery_agent = _s(bl.get("delivery_agent"))
    pre_carriage = _s(bl.get("pre_carriage_by"))
    place_receipt = _s(bl.get("place_of_receipt") or job.get("place_of_receipt"))

    # B/L reference uses Vessel/Voyage; Mother Vessel remains a booking/operation field,
    # not a replacement for the vessel printed on the B/L form.
    vessel = _s(bl.get("vessel") or job.get("vessel"))
    voyage = _s(bl.get("voyage") or job.get("voyage"))
    pol = _s(bl.get("port_of_loading") or job.get("pol"))
    pod = _s(bl.get("port_of_discharge") or job.get("pod"))
    place_delivery = _s(bl.get("place_of_delivery") or job.get("place_of_delivery") or pod)
    final_destination = _s(bl.get("final_destination"))

    freight = _s(bl.get("freight_term") or job.get("freight_term"), "PREPAID").upper()
    freight_payable = _s(bl.get("freight_payable_at"))
    issue_place = _s(bl.get("place_of_issue"), "THAILAND")
    originals = _s(bl.get("number_of_originals"), "3")
    bl_date = _date(bl.get("bl_date")) or _date(date.today())
    marks = _s(bl.get("marks_numbers"))
    goods = _s(bl.get("description_of_goods") or job.get("commodity"))
    hs = _s(bl.get("hs_code") or job.get("hs_code"))
    packages = _s(bl.get("package_qty"))
    gross = _num(bl.get("gross_weight"))
    cbm = _num(bl.get("measurement_cbm"), 3)

    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"BL_{bl_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=7 * mm,
        bottomMargin=8 * mm,
        title=f"Bill of Lading {bl_no}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )
    story = [_company_header(styles, bl_no), Spacer(1, 2 * mm)]

    if status.lower() in {"draft", "pending", "pending approval"}:
        label = "DRAFT" if status.lower() == "draft" else "PENDING APPROVAL"
        banner = Table([[Paragraph(label, styles["status"])]], colWidths=[TOTAL_W])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DRAFT),
            ("BOX", (0, 0), (-1, -1), 0.4, DRAFT),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        story.extend([banner, Spacer(1, 2 * mm)])

    # Parties block: keep the B/L form's visual hierarchy of shipper/consignee/notify.
    parties = Table([
        [_field("Shipper", shipper, styles), _field("B/L No.", bl_no, styles, tiny=True)],
        [_field("Consignee", consignee, styles), _field("For Delivery of Goods Please Apply to", delivery_agent, styles, tiny=True)],
        [_field("Notify Party", notify, styles), _field("Pre-Carriage by", pre_carriage, styles, tiny=True)],
    ], colWidths=[125 * mm, 65 * mm])
    parties.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story.extend([parties, Spacer(1, 1.2 * mm)])

    routing = Table([
        [_field("Place of Receipt", place_receipt, styles), _field("Ocean Vessel / Voyage No.", f"{vessel} {voyage}".strip(), styles), _field("Port of Loading", pol, styles)],
        [_field("Port of Discharge", pod, styles), _field("Place of Delivery", place_delivery, styles), _field("Final Destination (For The Merchant's Reference Only)", final_destination, styles, tiny=True)],
    ], colWidths=[63 * mm, 64 * mm, 63 * mm])
    routing.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([routing, Spacer(1, 1.2 * mm)])

    # Cargo grid follows the supplied B/L: Marks/Container+Seal, Packages, Description, Gross, CBM.
    cargo_rows = [[
        Paragraph("Marks and Numbers<br/>Container & Seal Numbers", styles["head"]),
        Paragraph("No. of Packages", styles["head"]),
        Paragraph("Description of Packages and Goods<br/>Packages Forwarded by Shipper", styles["head"]),
        Paragraph("Gross Weight Kgs", styles["head"]),
        Paragraph("Measurement CBM", styles["head"]),
    ]]

    if containers:
        for c in containers:
            container_label = _s(c.get("container_no"))
            seal_label = _s(c.get("seal_no") or c.get("seal"))
            cargo_rows.append([
                Paragraph(f"{container_label}<br/>Seal: {seal_label}", styles["tiny"]),
                Paragraph(_s(c.get("packages") or c.get("package_qty") or packages), styles["tiny"]),
                Paragraph(_s(c.get("description") or goods) + (f"<br/>HS CODE: {hs}" if hs else ""), styles["tiny"]),
                Paragraph(_num(c.get("gross_weight") or gross), styles["tiny"]),
                Paragraph(_num(c.get("cbm") or c.get("measurement_cbm") or cbm, 3), styles["tiny"]),
            ])
    else:
        cargo_rows.append([
            Paragraph(marks, styles["tiny"]),
            Paragraph(packages, styles["tiny"]),
            Paragraph(goods + (f"<br/>HS CODE: {hs}" if hs else ""), styles["tiny"]),
            Paragraph(gross, styles["tiny"]),
            Paragraph(cbm, styles["tiny"]),
        ])

    cargo = Table(cargo_rows, colWidths=[35 * mm, 22 * mm, 72 * mm, 30 * mm, 31 * mm], repeatRows=1)
    cargo.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("MINHEIGHT", (0, 1), (-1, -1), 46),
    ]))
    story.extend([cargo, Spacer(1, 1.2 * mm)])

    legal = (
        "RECEIVED by the Carrier the Goods as specified above in apparent good order and condition unless otherwise stated, to be transported to such place as agreed, authorized or permitted herein and subject to all the terms and conditions appearing on the front and back of this Bill of Lading to which the Merchant agrees by accepting this Bill of Lading, any local privileges and customs notwithstanding.\n\n"
        "The particulars given below as stated by the shipper and the weight, measure, quantity, condition, contents and value of the goods are unknown to the Carrier.\n\n"
        "IN WITNESS whereof this Bill of Lading has been signed if not otherwise stated above, the same being accomplished, the other(s), if any, to be void. If required by the Carrier one (1) original Bill of Lading must be surrendered duly endorsed in exchange for the Goods or delivery order."
    )
    freight_box = Table([
        [Paragraph("Freight and Disbursements", styles["head"]), Paragraph("Rate at KGS/Tons", styles["head"])],
        [Paragraph(f"{freight}", styles["center"]), Paragraph("", styles["tiny"])],
        [Paragraph("Prepaid", styles["center"]), Paragraph("Collect", styles["center"])],
    ], colWidths=[20 * mm, 20 * mm])
    freight_box.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    terms_box = Table([[Paragraph(legal.replace("\n", "<br/>"), styles["terms"])]], colWidths=[150 * mm])
    terms_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([Table([[freight_box, terms_box]], colWidths=[40 * mm, 150 * mm], style=TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ])), Spacer(1, 1.2 * mm)])

    issuance = Table([
        [Paragraph("Total", styles["label"]), "", "", Paragraph("Freight payable at", styles["label"]), Paragraph(freight_payable, styles["value"]), Paragraph("Place and date of issue", styles["label"]), Paragraph(f"{issue_place}<br/>{bl_date}", styles["value"])],
        ["", "", "", Paragraph("Number of original B/Ls", styles["label"]), Paragraph(originals, styles["center"]), Paragraph("Signed on behalf of the Carrier :", styles["label"]), Paragraph("<br/><br/>By ________________________", styles["signature"])],
    ], colWidths=[35 * mm, 22 * mm, 42 * mm, 31 * mm, 20 * mm, 20 * mm, 20 * mm])
    issuance.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(issuance)

    doc.build(story)
    return output_path
