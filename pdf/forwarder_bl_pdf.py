"""Company-issued Bill of Lading PDF for Smart Freight NTT.

Matches the supplied NATTAYARAAT sample structure without HBL/MBL labels.
One shipment may have many B/Ls; each B/L carries its own shipper/consignee
and cargo details while inheriting routing/vessel data from the Job.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import register_thai_fonts

THAI_FONT, THAI_FONT_BOLD = register_thai_fonts()
NAVY = colors.HexColor("#0F172A")
BLUE = colors.HexColor("#1F4E9E")
GOLD = colors.HexColor("#C9A227")
GREY = colors.HexColor("#E2E8F0")
LIGHT = colors.HexColor("#F8FAFC")
TEXT = colors.HexColor("#1E293B")
RED = colors.HexColor("#B91C1C")


def _clean_text(val: Any) -> str:
    """Strips internal codes (e.g. 'BP001 — ', 'C0001 — ', 'SP001 — ') for clean customer-facing PDF presentation."""
    if val is None:
        return ""
    text = str(val).strip()
    if not text or text.lower() in {"none", "nan", "nat"}:
        return ""
    if " — " in text:
        parts = text.split(" — ", 1)
        if len(parts[0]) <= 8 and (parts[0].isalnum() or parts[0].startswith(("BP", "C", "SP", "P", "CHG", "USR"))):
            return parts[1].strip()
    elif " - " in text:
        parts = text.split(" - ", 1)
        if len(parts[0]) <= 8 and (parts[0].isalnum() or parts[0].startswith(("BP", "C", "SP", "P", "CHG", "USR"))):
            return parts[1].strip()
    return text


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = _clean_text(value)
    return default if text.lower() in {"", "none", "nan", "nat"} else text


def _fmt_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%b-%Y")
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d-%b-%Y")
    except Exception:
        return _s(value)


def _fmt_num(value: Any, precision: int = 2) -> str:
    try:
        v = float(value or 0)
        return "" if v == 0 else f"{v:,.{precision}f}"
    except (TypeError, ValueError):
        return ""


def _styles():
    base = getSampleStyleSheet()
    return {
        "small": ParagraphStyle("small", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.3, leading=9, textColor=TEXT),
        "label": ParagraphStyle("label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9, textColor=NAVY),
        "value": ParagraphStyle("value", parent=base["Normal"], fontName=THAI_FONT, fontSize=8.2, leading=10, textColor=TEXT),
        "head": ParagraphStyle("head", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.2, leading=10, textColor=colors.white, alignment=TA_LEFT),
        "title": ParagraphStyle("title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=17, leading=20, textColor=NAVY, alignment=TA_CENTER),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=10, leading=12, textColor=GOLD, alignment=TA_CENTER),
        "status": ParagraphStyle("status", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=10, textColor=colors.white, alignment=TA_CENTER),
    }


def _cell(label: str, value: Any, styles: Dict[str, Any], height: float = 16):
    text = f"<b>{label}</b><br/>{_s(value)}"
    return Paragraph(text, styles["value"])


def _payload(bl_id: int) -> Dict[str, Any]:
    from managers.bl_workflow_service import get_bl
    from database.connection import get_connection

    bl = get_bl(bl_id)
    if not bl:
        raise ValueError(f"B/L {bl_id} not found.")

    job = {}
    if bl.get("job_no"):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM shipments WHERE job_no=%s AND tenant_id=%s", (bl["job_no"], bl.get("tenant_id", "default")))
                row = cur.fetchone()
                if row:
                    job = dict(row)

    containers = []
    try:
        from managers.bl_manager import list_bl_containers
        containers = list_bl_containers(bl_id) or []
    except Exception:
        containers = []

    return {"bl": bl, "job": job, "containers": containers}


def generate_forwarder_bl_pdf(bl_id: int, output_path: str | None = None) -> str:
    payload = _payload(int(bl_id))
    bl = payload["bl"]
    job = payload["job"]
    containers = payload["containers"]
    styles = _styles()

    bl_no = _s(bl.get("bl_no"), "DRAFT")
    status = _s(bl.get("approval_status"), "Draft")
    shipper = _s(bl.get("shipper"), "")
    consignee = _s(bl.get("consignee"), "")
    notify = _s(bl.get("notify_party"), "SAME AS CONSIGNEE" if consignee else "")
    vessel = _s(bl.get("vessel") or job.get("vessel"))
    voyage = _s(bl.get("voyage") or job.get("voyage"))
    pol = _s(bl.get("port_of_loading") or job.get("pol"))
    pod = _s(bl.get("port_of_discharge") or job.get("pod"))
    place_delivery = _s(bl.get("place_of_delivery") or job.get("place_of_delivery") or pod)
    freight = _s(bl.get("freight_term") or job.get("freight_term"), "PREPAID").upper()

    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"BL_{bl_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=10*mm,
        rightMargin=10*mm,
        topMargin=9*mm,
        bottomMargin=12*mm,
        title=f"Bill of Lading {bl_no}",
        author=COMPANY.get("name", "NATTAYARAAT CO., LTD."),
    )

    story = []
    company = (
        f"<b>{COMPANY.get('name','NATTAYARAAT CO., LTD.')}</b><br/>"
        f"{COMPANY.get('address_line1','')}<br/>"
        f"{COMPANY.get('address_line2','')} {COMPANY.get('address_line3','')}<br/>"
        f"Tax ID: {COMPANY.get('tax_id','')} · Tel: {COMPANY.get('tel','')} · Email: {COMPANY.get('email','')}"
    )

    from pdf.bl_document_renderer import resolve_document_title
    doc_title = resolve_document_title(bl=bl, job=job)

    header = Table([
        [Paragraph(f"<b>{COMPANY.get('short_name','NATTA')}</b>", styles["title"]), Paragraph(company, styles["small"]), Paragraph(doc_title, styles["title"])],
        ["", "", Paragraph(f"<b>{bl_no}</b>", styles["sub"])],
    ], colWidths=[28*mm, 94*mm, 64*mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2), ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    story += [header, Spacer(1, 2*mm)]

    if status.lower() in {"draft", "pending approval", "pending"}:
        banner = "DRAFT — NOT FOR SHIPPING OR NEGOTIATION" if status.lower() == "draft" else "PENDING APPROVAL"
        bt = Table([[Paragraph(banner, styles["status"])]], colWidths=[186*mm])
        bt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), RED), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
        story += [bt, Spacer(1, 2*mm)]

    parties = Table([
        [_cell("Shipper", shipper, styles), _cell("Consignee", consignee, styles)],
        [_cell("Notify Party", notify, styles), _cell("Place of Receipt", bl.get("place_of_receipt") or pol, styles)],
        [_cell("Port of Loading", pol, styles), _cell("Port of Discharge", pod, styles)],
        [_cell("Place of Delivery", place_delivery, styles), _cell("Final Destination", bl.get("final_destination") or place_delivery, styles)],
    ], colWidths=[93*mm, 93*mm], rowHeights=[22*mm, 18*mm, 18*mm, 18*mm])
    parties.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, GREY),
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story += [parties, Spacer(1, 2*mm)]

    routing = Table([
        [_cell("Ocean Vessel / Voyage No.", f"{vessel} {voyage}".strip(), styles), _cell("Freight", freight, styles), _cell("ETD / ETA", f"{_fmt_date(bl.get('etd') or job.get('etd'))} / {_fmt_date(bl.get('eta') or job.get('eta'))}", styles)],
        [_cell("B/L Issue Date", _fmt_date(bl.get("bl_date")) or _fmt_date(date.today()), styles), _cell("Place of Issue", bl.get("place_of_issue") or "THAILAND", styles), _cell("Originals", bl.get("number_of_originals") or 3, styles)],
    ], colWidths=[93*mm, 46.5*mm, 46.5*mm])
    routing.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, GREY), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BACKGROUND", (0,0), (-1,-1), LIGHT),
    ]))
    story += [routing, Spacer(1, 2*mm)]

    container_rows = [[
        Paragraph("Container & Seal Numbers", styles["head"]),
        Paragraph("Packages", styles["head"]),
        Paragraph("Gross Weight Kgs", styles["head"]),
        Paragraph("Measurement CBM", styles["head"]),
    ]]
    if containers:
        for c in containers:
            container_rows.append([
                Paragraph(f"{_s(c.get('container_no'))} / {_s(c.get('container_type') or c.get('size'))}<br/>Seal: {_s(c.get('seal_no') or c.get('seal'))}", styles["small"]),
                Paragraph(_s(c.get('packages') or c.get('package_qty')), styles["small"]),
                Paragraph(_fmt_num(c.get('gross_weight')), styles["small"]),
                Paragraph(_fmt_num(c.get('cbm') or c.get('measurement_cbm'), 3), styles["small"]),
            ])
    else:
        container_rows.append([
            Paragraph(_s(bl.get("marks_numbers") or ""), styles["small"]),
            Paragraph(_s(bl.get("package_qty")), styles["small"]),
            Paragraph(_fmt_num(bl.get("gross_weight")), styles["small"]),
            Paragraph(_fmt_num(bl.get("measurement_cbm"), 3), styles["small"]),
        ])

    manifest = Table(container_rows, colWidths=[84*mm, 25*mm, 35*mm, 42*mm], repeatRows=1)
    manifest.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, GREY), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [manifest, Spacer(1, 2*mm)]

    goods = _s(bl.get("description_of_goods") or job.get("commodity"), "")
    hs = _s(bl.get("hs_code") or job.get("hs_code"), "")
    remarks = _s(bl.get("remarks") or bl.get("special_instructions"), "")
    cargo = Table([
        [Paragraph("Description of Packages and Goods", styles["head"])],
        [Paragraph(goods.replace("\n", "<br/>"), styles["value"])],
        [Paragraph(f"HS CODE: {hs}" if hs else "", styles["small"])],
        [Paragraph(remarks.replace("\n", "<br/>"), styles["small"])],
    ], colWidths=[186*mm])
    cargo.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("GRID", (0,0), (-1,-1), 0.5, GREY),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [cargo, Spacer(1, 2*mm)]

    terms = (
        "RECEIVED by NATTAYARAAT CO., LTD. the goods as specified above in apparent good order and condition unless otherwise stated, "
        "to be transported subject to the applicable terms and conditions of this Bill of Lading. Particulars are based on shipper's declaration. "
        f"FREIGHT {freight}. SHIPPER'S LOAD, COUNT & SEAL."
    )
    terms_tbl = Table([[Paragraph(terms, styles["small"])]], colWidths=[186*mm])
    terms_tbl.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, GREY), ("BACKGROUND", (0,0), (-1,-1), LIGHT),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story += [terms_tbl, Spacer(1, 2*mm)]

    footer = Table([
        [Paragraph(f"B/L No. <b>{bl_no}</b><br/>Shipment: {_s(bl.get('job_no'))}<br/>Consol Seq: {_s(bl.get('consol_seq'), '1')}", styles["small"]), Paragraph("For and on behalf of<br/><b>NATTAYARAAT CO., LTD.</b>", styles["small"])],
    ], colWidths=[93*mm, 93*mm])
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,-1), 0.6, NAVY),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("TOPPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(footer)

    doc.build(story)
    return output_path
