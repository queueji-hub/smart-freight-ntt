"""Pure company-issued Bill of Lading renderer.

No database access. The caller must provide a validated payload assembled by a
manager/service. The renderer only formats data into PDF output.
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
NAVY = colors.HexColor("#0F172A")
BLUE = colors.HexColor("#1F4E9E")
GOLD = colors.HexColor("#C9A227")
GREY = colors.HexColor("#CBD5E1")
LIGHT = colors.HexColor("#F8FAFC")
TEXT = colors.HexColor("#1E293B")
DRAFT = colors.HexColor("#B91C1C")


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
        "body": ParagraphStyle("body", parent=base["Normal"], fontName=FONT, fontSize=7.8, leading=9.5, textColor=TEXT),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName=FONT, fontSize=6.7, leading=8, textColor=TEXT),
        "label": ParagraphStyle("label", parent=base["Normal"], fontName=FONT_BOLD, fontSize=6.8, leading=8.4, textColor=NAVY),
        "title": ParagraphStyle("title", parent=base["Normal"], fontName=FONT_BOLD, fontSize=16, leading=18, textColor=NAVY, alignment=TA_CENTER),
        "number": ParagraphStyle("number", parent=base["Normal"], fontName=FONT_BOLD, fontSize=10, leading=12, textColor=GOLD, alignment=TA_CENTER),
        "head": ParagraphStyle("head", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.2, leading=8.5, textColor=colors.white, alignment=TA_LEFT),
        "status": ParagraphStyle("status", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8, leading=9.5, textColor=colors.white, alignment=TA_CENTER),
    }


def _field(label: str, value: Any, styles: Dict[str, Any]) -> Paragraph:
    return Paragraph(f"<b>{label}</b><br/>{_s(value)}", styles["body"])


def generate_company_bl_pdf(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Render a validated company-issued B/L payload to an A4 PDF."""
    if not isinstance(payload, dict) or "bl" not in payload:
        raise ValueError("B/L PDF requires a validated payload dict with a 'bl' record.")

    bl = dict(payload.get("bl") or {})
    job = dict(payload.get("job") or {})
    containers = list(payload.get("containers") or [])
    styles = _styles()

    bl_no = _s(bl.get("bl_no"), "DRAFT")
    status = _s(bl.get("approval_status"), "Draft")
    vessel = _s(bl.get("vessel") or job.get("vessel") or job.get("mother_vessel"))
    voyage = _s(bl.get("voyage") or job.get("voyage"))
    pol = _s(bl.get("port_of_loading") or job.get("pol"))
    pod = _s(bl.get("port_of_discharge") or job.get("pod"))
    place_delivery = _s(bl.get("place_of_delivery") or job.get("place_of_delivery") or pod)
    freight = _s(bl.get("freight_term") or job.get("freight_term"), "PREPAID").upper()

    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"BL_{bl_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4, leftMargin=10*mm, rightMargin=10*mm,
        topMargin=9*mm, bottomMargin=14*mm, title=f"Bill of Lading {bl_no}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )
    story = []

    company = (
        f"<b>{COMPANY.get('name','NATTAYARAAT CO., LTD.')}</b><br/>"
        f"{COMPANY.get('address_line1','')}<br/>"
        f"{COMPANY.get('address_line2','')} {COMPANY.get('address_line3','')}<br/>"
        f"Tax ID: {COMPANY.get('tax_id','')} · Tel: {COMPANY.get('tel','')} · Email: {COMPANY.get('email','')}"
    )
    header = Table([
        [Paragraph(company, styles["small"]), Paragraph("BILL OF LADING", styles["title"]), Paragraph(f"<b>{bl_no}</b>", styles["number"])],
    ], colWidths=[70*mm, 70*mm, 46*mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LINEBELOW", (0,0), (-1,-1), 1, BLUE),
        ("LEFTPADDING", (0,0), (-1,-1), 2), ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [header, Spacer(1, 2*mm)]

    if status.lower() in {"draft", "pending", "pending approval"}:
        label = "DRAFT — NOT FOR SHIPPING OR NEGOTIATION" if status.lower() == "draft" else "PENDING APPROVAL"
        banner = Table([[Paragraph(label, styles["status"])]], colWidths=[186*mm])
        banner.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), DRAFT), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
        story += [banner, Spacer(1, 2*mm)]

    parties = Table([
        [_field("Shipper", bl.get("shipper"), styles), _field("Consignee", bl.get("consignee"), styles)],
        [_field("Notify Party", bl.get("notify_party") or "SAME AS CONSIGNEE", styles), _field("Place of Receipt", bl.get("place_of_receipt") or pol, styles)],
        [_field("Port of Loading", pol, styles), _field("Port of Discharge", pod, styles)],
        [_field("Place of Delivery", place_delivery, styles), _field("Final Destination", bl.get("final_destination") or place_delivery, styles)],
    ], colWidths=[93*mm, 93*mm])
    parties.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.45, GREY), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [parties, Spacer(1, 2*mm)]

    routing = Table([
        [_field("Ocean Vessel / Voyage No.", f"{vessel} {voyage}".strip(), styles), _field("ETD / ETA", f"{_date(bl.get('etd') or job.get('etd'))} / {_date(bl.get('eta') or job.get('eta'))}", styles)],
        [_field("Freight", freight, styles), _field("Place and Date of Issue", f"{_s(bl.get('place_of_issue'), 'THAILAND')} / {_date(bl.get('bl_date')) or _date(date.today())}", styles)],
    ], colWidths=[93*mm, 93*mm])
    routing.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.45, GREY), ("BACKGROUND", (0,0), (-1,-1), LIGHT),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [routing, Spacer(1, 2*mm)]

    manifest = [[Paragraph("Container & Seal Numbers", styles["head"]), Paragraph("Packages", styles["head"]), Paragraph("Gross Weight Kgs", styles["head"]), Paragraph("Measurement CBM", styles["head"])]]
    if containers:
        for c in containers:
            manifest.append([
                Paragraph(f"{_s(c.get('container_no'))} / {_s(c.get('container_type') or c.get('size'))}<br/>Seal: {_s(c.get('seal_no') or c.get('seal'))}", styles["small"]),
                Paragraph(_s(c.get('packages') or c.get('package_qty')), styles["small"]),
                Paragraph(_num(c.get('gross_weight')), styles["small"]),
                Paragraph(_num(c.get('cbm') or c.get('measurement_cbm'), 3), styles["small"]),
            ])
    else:
        manifest.append([
            Paragraph(_s(bl.get("marks_numbers")), styles["small"]),
            Paragraph(_s(bl.get("package_qty")), styles["small"]),
            Paragraph(_num(bl.get("gross_weight")), styles["small"]),
            Paragraph(_num(bl.get("measurement_cbm"), 3), styles["small"]),
        ])
    mt = Table(manifest, colWidths=[84*mm, 25*mm, 35*mm, 42*mm], repeatRows=1)
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE), ("GRID", (0,0), (-1,-1), 0.45, GREY),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [mt, Spacer(1, 2*mm)]

    goods = _s(bl.get("description_of_goods") or job.get("commodity"), "")
    hs = _s(bl.get("hs_code") or job.get("hs_code"), "")
    remarks = _s(bl.get("remarks") or bl.get("special_instructions"), "")
    cargo = Table([
        [Paragraph("Description of Packages and Goods", styles["head"])],
        [Paragraph(goods.replace("\n", "<br/>"), styles["body"])],
        [Paragraph(f"HS CODE: {hs}" if hs else "", styles["small"])],
        [Paragraph(remarks.replace("\n", "<br/>"), styles["small"])],
    ], colWidths=[186*mm])
    cargo.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("GRID", (0,0), (-1,-1), 0.45, GREY),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [cargo, Spacer(1, 2*mm)]

    terms = (
        "RECEIVED by NATTAYARAAT CO., LTD. the goods as specified above in apparent good order and condition unless otherwise stated. "
        "Particulars are as declared by the shipper. FREIGHT " + freight + ". SHIPPER'S LOAD, COUNT & SEAL."
    )
    terms_tbl = Table([[Paragraph(terms, styles["small"])]], colWidths=[186*mm])
    terms_tbl.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.45, GREY), ("BACKGROUND", (0,0), (-1,-1), LIGHT),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story += [terms_tbl, Spacer(1, 3*mm)]

    signature = Table([[Paragraph("For and on behalf of NATTAYARAAT CO., LTD.", styles["label"]), Paragraph(f"B/L No.: <b>{bl_no}</b><br/>Consol Seq: <b>{_s(bl.get('consol_seq'), '1')}</b>", styles["small"])]], colWidths=[120*mm, 66*mm])
    signature.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,-1), 0.6, GREY),
        ("TOPPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(signature)

    doc.build(story)
    return output_path
