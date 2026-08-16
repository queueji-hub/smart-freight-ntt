"""Pure company-issued Bill of Lading renderer.

The renderer mirrors the approved BL workbook form structure and consumes only a
validated payload assembled by the manager/service layer. It never queries the
Database.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import register_thai_fonts

FONT, FONT_BOLD = register_thai_fonts()
BORDER = colors.HexColor("#4B5563")
HEADER = colors.HexColor("#E5E7EB")
TEXT = colors.HexColor("#111827")
DRAFT = colors.HexColor("#B91C1C")

# Eight columns corresponding to the supplied workbook grid A:H.
COLS = [21*mm, 16*mm, 22*mm, 20*mm, 46*mm, 21*mm, 22*mm, 22*mm]
TOTAL_W = sum(COLS)


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


def _styles():
    base = getSampleStyleSheet()
    return {
        "label": ParagraphStyle("bl_label", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.8, leading=8.2, textColor=TEXT),
        "value": ParagraphStyle("bl_value", parent=base["Normal"], fontName=FONT, fontSize=7.2, leading=8.8, textColor=TEXT),
        "tiny": ParagraphStyle("bl_tiny", parent=base["Normal"], fontName=FONT, fontSize=6.2, leading=7.5, textColor=TEXT),
        "center": ParagraphStyle("bl_center", parent=base["Normal"], fontName=FONT_BOLD, fontSize=14, leading=16, textColor=TEXT, alignment=TA_CENTER),
        "number": ParagraphStyle("bl_number", parent=base["Normal"], fontName=FONT_BOLD, fontSize=9.5, leading=11, textColor=TEXT, alignment=TA_CENTER),
        "head": ParagraphStyle("bl_head", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.8, leading=8.0, textColor=TEXT, alignment=TA_CENTER),
        "terms": ParagraphStyle("bl_terms", parent=base["Normal"], fontName=FONT, fontSize=6.2, leading=7.5, textColor=TEXT),
        "status": ParagraphStyle("bl_status", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.5, leading=9, textColor=colors.white, alignment=TA_CENTER),
    }


def _field(label: str, value: Any, styles: Dict[str, Any]) -> Paragraph:
    return Paragraph(f"<b>{label}</b><br/>{_s(value)}", styles["value"])


def _small_field(label: str, value: Any, styles: Dict[str, Any]) -> Paragraph:
    return Paragraph(f"<b>{label}</b><br/>{_s(value)}", styles["tiny"])


def _box(data, widths, *, background=None, padding=3, v_align="TOP"):
    table = Table(data, colWidths=widths)
    styles = [
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), v_align),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    if background:
        styles.append(("BACKGROUND", (0, 0), (-1, -1), background))
    table.setStyle(TableStyle(styles))
    return table


def generate_company_bl_pdf(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Render the supplied BL form structure to A4 PDF."""
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
    delivery_agent = _s(bl.get("delivery_agent") or bl.get("place_of_delivery") or job.get("place_of_delivery"))
    pre_carriage = _s(bl.get("pre_carriage_by"), "")
    place_receipt = _s(bl.get("place_of_receipt") or job.get("place_of_receipt"))
    vessel = _s(bl.get("vessel") or job.get("mother_vessel") or job.get("vessel"))
    voyage = _s(bl.get("voyage") or job.get("voyage"))
    pol = _s(bl.get("port_of_loading") or job.get("pol"))
    pod = _s(bl.get("port_of_discharge") or job.get("pod"))
    place_delivery = _s(bl.get("place_of_delivery") or job.get("place_of_delivery") or pod)
    final_destination = _s(bl.get("final_destination"), "")
    freight = _s(bl.get("freight_term") or job.get("freight_term"), "PREPAID").upper()
    freight_payable = _s(bl.get("freight_payable_at"), "")
    issue_place = _s(bl.get("place_of_issue"), "THAILAND")
    originals = _s(bl.get("number_of_originals"), "3")
    bl_date = _date(bl.get("bl_date")) or _date(date.today())
    goods = _s(bl.get("description_of_goods") or job.get("commodity"), "")
    hs = _s(bl.get("hs_code") or job.get("hs_code"), "")
    marks = _s(bl.get("marks_numbers"), "")

    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"BL_{bl_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=7*mm,
        bottomMargin=8*mm,
        title=f"Bill of Lading {bl_no}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )

    story = []

    # Header band: mirrors workbook A2:D4 + E2:H2 + E3:H5.
    header = Table([
        [
            Paragraph("BILL OF LADING", styles["center"]),
            Paragraph(f"B/L No. <b>{bl_no}</b>", styles["number"]),
        ]
    ], colWidths=[TOTAL_W * 0.68, TOTAL_W * 0.32])
    header.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.8, BORDER),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [header, Spacer(1, 1.5*mm)]

    if status.lower() in {"draft", "pending", "pending approval"}:
        label = "DRAFT" if status.lower() == "draft" else "PENDING APPROVAL"
        banner = Table([[Paragraph(label, styles["status"])]], colWidths=[TOTAL_W])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DRAFT),
            ("BOX", (0,0), (-1,-1), 0.4, DRAFT),
            ("TOPPADDING", (0,0), (-1,-1), 2.5), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ]))
        story += [banner, Spacer(1, 1.5*mm)]

    # Row 5: Shipper + B/L reference area.
    top_parties = Table([
        [
            _field("Shipper", shipper, styles),
            _small_field("B/L No.", bl_no, styles),
        ],
        [
            _field("Consignee", consignee, styles),
            _field("", "", styles),
        ],
        [
            _field("Notify Party", notify, styles),
            _field("For Delivery of Goods Please Apply to", delivery_agent, styles),
        ],
    ], colWidths=[TOTAL_W * 0.68, TOTAL_W * 0.32])
    top_parties.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, BORDER),
        ("SPAN", (1,1), (1,1)),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [top_parties, Spacer(1, 1.2*mm)]

    # Routing rows 7-9 from the workbook.
    routing = Table([
        [
            _field("Pre-Carriage by", pre_carriage, styles),
            _field("Place of Receipt", place_receipt, styles),
            _field("", "", styles),
        ],
        [
            _field("Ocean Vessel/Voyage No.", f"{vessel} {voyage}".strip(), styles),
            _field("Port of Loading", pol, styles),
            _field("", "", styles),
        ],
        [
            _field("Port of Discharge", pod, styles),
            _field("Place of Delivery", place_delivery, styles),
            _field("Final Destination (For The Merchant's Reference Only)", final_destination, styles),
        ],
    ], colWidths=[TOTAL_W*0.33, TOTAL_W*0.34, TOTAL_W*0.33])
    routing.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, BORDER),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [routing, Spacer(1, 1.2*mm)]

    # Cargo header + rows 10-12.
    cargo_head = [
        Paragraph("Marks and Numbers<br/>Container & Seal Numbers", styles["head"]),
        Paragraph("No. of Packages", styles["head"]),
        Paragraph("Description of Packages and Goods<br/>Packages Forwarded by Shipper", styles["head"]),
        Paragraph("Gross Weight Kgs", styles["head"]),
        Paragraph("Measurement CBM", styles["head"]),
    ]
    cargo_widths = [TOTAL_W*0.18, TOTAL_W*0.12, TOTAL_W*0.38, TOTAL_W*0.16, TOTAL_W*0.16]
    rows = [cargo_head]
    if containers:
        for c in containers:
            rows.append([
                Paragraph(f"{_s(c.get('container_no'))}<br/>Seal: {_s(c.get('seal_no') or c.get('seal'))}", styles["tiny"]),
                Paragraph(_s(c.get('packages') or c.get('package_qty') or bl.get('package_qty')), styles["tiny"]),
                Paragraph(_s(c.get('description') or goods), styles["tiny"]),
                Paragraph(_num(c.get('gross_weight') or bl.get('gross_weight')), styles["tiny"]),
                Paragraph(_num(c.get('cbm') or c.get('measurement_cbm') or bl.get('measurement_cbm'), 3), styles["tiny"]),
            ])
    else:
        rows.append([
            Paragraph(marks, styles["tiny"]),
            Paragraph(_s(bl.get('package_qty')), styles["tiny"]),
            Paragraph(goods + (f"<br/>HS CODE: {hs}" if hs else ""), styles["tiny"]),
            Paragraph(_num(bl.get('gross_weight')), styles["tiny"]),
            Paragraph(_num(bl.get('measurement_cbm'), 3), styles["tiny"]),
        ])
    cargo_table = Table(rows, colWidths=cargo_widths, repeatRows=1)
    cargo_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, BORDER),
        ("BACKGROUND", (0,0), (-1,0), HEADER),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("MINHEIGHT", (0,1), (-1,-1), 32),
    ]))
    story += [cargo_table, Spacer(1, 1.2*mm)]

    # Freight + terms row 13.
    terms = (
        "RECEIVED by the Carrier the Goods as specified above in apparent good order and condition unless otherwise stated, "
        "to be transported to such place as agreed, authorized or permitted herein and subject to all the terms and conditions appearing on the front and back of this Bill of Lading to which the Merchant agrees by accepting this Bill of Lading, any local privileges and customs notwithstanding.\n\n"
        "The particulars given below as stated by the shipper and the weight, measure, quantity, condition, contents and value of the goods are unknown to the Carrier.\n\n"
        "IN WITNESS whereof this Bill of Lading has been signed if not otherwise stated above, the same being accomplished, the other(s), if any, to be void. "
        "If required by the Carrier one (1) original Bill of Lading must be surrendered duly endorsed in exchange for the Goods or delivery order."
    )
    freight_left = Table([
        [Paragraph("Freight and Disbursements", styles["head"]), Paragraph("Rate at KGS/Tons", styles["head"])],
        [Paragraph("", styles["tiny"]), Paragraph("", styles["tiny"])],
        [Paragraph("Prepaid", styles["label"]), Paragraph("Collect", styles["label"])],
    ], colWidths=[TOTAL_W*0.11, TOTAL_W*0.10])
    freight_left.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, BORDER),
        ("BACKGROUND", (0,0), (-1,0), HEADER),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    terms_box = Table([[Paragraph(terms.replace("\n", "<br/>"), styles["terms"])]], colWidths=[TOTAL_W*0.79])
    terms_box.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, BORDER),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    freight_row = Table([[freight_left, terms_box]], colWidths=[TOTAL_W*0.21, TOTAL_W*0.79])
    freight_row.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0)]))
    story += [freight_row, Spacer(1, 1.2*mm)]

    # Total + issuance/signature rows 15-17.
    total = Table([[Paragraph("Total", styles["label"]), "", "", "", ""]], colWidths=cargo_widths)
    total.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, BORDER),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story += [total, Spacer(1, 1.2*mm)]

    issuance = Table([
        ["", "", Paragraph("Freight payable at", styles["label"]), Paragraph(freight_payable, styles["value"]), Paragraph("Place and date of issue", styles["label"]), Paragraph(f"{issue_place}<br/>{bl_date}", styles["value"])],
        ["", "", Paragraph("Number of original B/Ls", styles["label"]), Paragraph(originals, styles["value"]), Paragraph("Signed on behalf of the Carrier :<br/><br/><br/>By", styles["label"]), ""],
    ], colWidths=[COLS[0], COLS[1], COLS[2], COLS[3], COLS[4], sum(COLS[5:])])
    issuance.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, BORDER),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [issuance]

    doc.build(story)
    return output_path
