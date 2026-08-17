"""
Bill of Lading (B/L) PDF Generator — Phase J5
Enterprise Freight Forwarding Document Engine using ReportLab with Thai Font Support.

Supports:
  - HBL & MBL Documents
  - Read-Only Payload Assembly from B/L + Job + Containers
  - Status Watermark & Title Banners (Draft, Submitted, Approved, Issued, Surrendered, Cancelled)
  - Multi-Page Container Manifest with Repeated Header
  - 100% NULL-Safe String Normalization (_clean_str)
  - Thai & Unicode Character Encoding
  - Page X of Y Pagination via NumberedCanvas
"""

import os
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.pdfgen.canvas import Canvas

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import register_thai_fonts

# Register fonts once
THAI_FONT, THAI_FONT_BOLD = register_thai_fonts()

# Color Palette
BRAND_BLUE = colors.HexColor("#1F4E9E")
BRAND_NAVY = colors.HexColor("#0F172A")
BRAND_GOLD = colors.HexColor("#C9A227")
BORDER_GREY = colors.HexColor("#D1D5DB")
BG_LIGHT_GREY = colors.HexColor("#F8FAFC")
TEXT_DARK = colors.HexColor("#1E293B")
STATUS_RED = colors.HexColor("#DC2626")
STATUS_GREEN = colors.HexColor("#16A34A")

# =========================================================
# NULL-SAFE CLEANERS & FORMATTERS
# =========================================================

def _clean_str(val, default="") -> str:
    """NULL-safe string cleaner. Returns default if None, empty, or 'None'/'nan'."""
    if val is None:
        return default
    v = str(val).strip()
    return default if not v or v.lower() in ("none", "nan", "nat") else v


def _fmt_date(val) -> str:
    """Format date to DD-Mon-YYYY."""
    if not val:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%d-%b-%Y")
    v_str = str(val).strip()
    if not v_str or v_str.lower() in ("none", "nan", "nat"):
        return ""
    try:
        return datetime.strptime(v_str[:10], "%Y-%m-%d").strftime("%d-%b-%Y")
    except Exception:
        return v_str


def _fmt_num(val, precision=2, unit="") -> str:
    """Safely format numbers with commas and optional unit."""
    if val is None:
        return ""
    try:
        f = float(val)
        if f == 0.0:
            return ""
        formatted = f"{f:,.{precision}f}"
        return f"{formatted} {unit}".strip() if unit else formatted
    except (ValueError, TypeError):
        return ""


# =========================================================
# MULTI-PAGE NUMBERED CANVAS
# =========================================================

class NumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont(THAI_FONT, 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Bottom Line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(15*mm, 13*mm, A4[0] - 15*mm, 13*mm)

        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 15*mm, 9*mm, page_text)
        self.drawString(15*mm, 9*mm, f"{COMPANY.get('name', 'NATTAYARAAT CO., LTD.')} — Bill of Lading Document")
        self.restoreState()


# =========================================================
# STYLES ENGINE
# =========================================================

def _get_styles():
    base = getSampleStyleSheet()
    return {
        "company_name": ParagraphStyle(
            "cn", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=16,
            textColor=BRAND_BLUE, leading=19, spaceAfter=2
        ),
        "company_addr": ParagraphStyle(
            "ca", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8,
            textColor=TEXT_DARK, leading=11
        ),
        "doc_title": ParagraphStyle(
            "dt", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=16,
            textColor=BRAND_NAVY, alignment=TA_CENTER, leading=20
        ),
        "doc_subtitle": ParagraphStyle(
            "ds", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=11,
            textColor=BRAND_GOLD, alignment=TA_CENTER, leading=14
        ),
        "box_header": ParagraphStyle(
            "bh", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8,
            textColor=colors.white, leading=10, alignment=TA_LEFT
        ),
        "label_bold": ParagraphStyle(
            "lb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8,
            textColor=BRAND_NAVY, leading=10
        ),
        "value_text": ParagraphStyle(
            "vt", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8,
            textColor=TEXT_DARK, leading=10
        ),
        "value_text_small": ParagraphStyle(
            "vts", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=7.5,
            textColor=TEXT_DARK, leading=9.5
        ),
        "manifest_head": ParagraphStyle(
            "mh", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=8,
            textColor=colors.white, alignment=TA_CENTER, leading=10
        ),
        "manifest_cell": ParagraphStyle(
            "mc", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=8,
            textColor=TEXT_DARK, alignment=TA_CENTER, leading=10
        ),
        "status_banner": ParagraphStyle(
            "sb", parent=base["Normal"],
            fontName=THAI_FONT_BOLD, fontSize=9,
            textColor=colors.white, alignment=TA_CENTER, leading=12
        ),
        "terms_text": ParagraphStyle(
            "tt", parent=base["Normal"],
            fontName=THAI_FONT, fontSize=6.5,
            textColor=colors.HexColor("#475569"), leading=8
        ),
    }


# =========================================================
# DATA PAYLOAD LOADER (READ-ONLY)
# =========================================================

def assemble_bl_pdf_payload(bl_id_or_no) -> Dict[str, Any]:
    """
    Assembles a complete, immutable data payload for B/L PDF generation.
    Reads B/L header, linked Job/Shipment data, and linked Containers (via bl_containers).
    Does ZERO database writes.
    """
    from managers.bl_manager import get_bl, list_bl_containers
    from database.connection import get_connection

    # Fetch B/L
    if isinstance(bl_id_or_no, int) or (isinstance(bl_id_or_no, str) and bl_id_or_no.isdigit()):
        bl_doc = get_bl(int(bl_id_or_no))
    else:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM bills_of_lading WHERE bl_no = %s", (str(bl_id_or_no),))
                row = cur.fetchone()
                bl_doc = dict(row) if row else None

    if not bl_doc:
        raise ValueError(f"B/L '{bl_id_or_no}' not found.")

    bl_id = bl_doc["id"]
    job_no = bl_doc.get("job_no")

    # Fetch linked containers via bl_containers junction
    containers = list_bl_containers(bl_id) or []

    # Fetch linked Job/Shipment
    job_doc = None
    if job_no:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM shipments WHERE job_no = %s", (job_no,))
                jrow = cur.fetchone()
                if jrow:
                    job_doc = dict(jrow)

    # Fetch linked Booking if booking_no present
    booking_doc = None
    booking_no = bl_doc.get("booking_no") or (job_doc.get("booking_no") if job_doc else None)
    if booking_no:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM bookings WHERE booking_no = %s", (booking_no,))
                brow = cur.fetchone()
                if brow:
                    booking_doc = dict(brow)

    return {
        "bl": bl_doc,
        "job": job_doc or {},
        "booking": booking_doc or {},
        "containers": containers,
        "company": COMPANY,
    }


# =========================================================
# PDF BUILDER ENGINE
# =========================================================

def generate_bl_pdf(bl_source: Any, output_path: str = None) -> str:
    """
    Generate Bill of Lading PDF from a B/L dict or B/L ID/no.
    Uses the canonical Ocean Bill of Lading renderer matching the approved sample layout.
    
    Arguments:
      bl_source: Can be a prepared payload dict, a B/L record dict, or a bl_id / bl_no (int/str).
      output_path: Optional output path. If None, saves in OUTPUT_DIR with deterministic name.

    Returns:
      Absolute output file path string.
    """
    from pdf.bl_document_renderer import generate_company_bl_pdf

    # Resolve payload
    if isinstance(bl_source, dict) and "bl" in bl_source and "containers" in bl_source:
        payload = bl_source
    elif isinstance(bl_source, dict) and "bl_no" in bl_source:
        # Given single B/L record dict
        bl_id = bl_source.get("id") or bl_source.get("bl_no")
        try:
            payload = assemble_bl_pdf_payload(bl_id)
        except Exception:
            payload = {
                "bl": bl_source,
                "job": bl_source.get("job") or {},
                "containers": bl_source.get("containers") or [],
            }
    else:
        payload = assemble_bl_pdf_payload(bl_source)

    return generate_company_bl_pdf(payload, output_path)

    styles = _get_styles()
    story = []

    # ---------------------------------------------------------
    # 1. HEADER SECTION (COMPANY LOGO & DOC TITLE)
    # ---------------------------------------------------------
    logo_path = COMPANY.get("logo_path")
    if logo_path and Path(logo_path).exists():
        from reportlab.lib.utils import ImageReader
        try:
            ir = ImageReader(logo_path)
            iw, ih = ir.getSize()
            scale = min(42*mm / iw, 24*mm / ih)
            logo_img = Image(logo_path, width=iw*scale, height=ih*scale)
        except Exception:
            logo_img = Paragraph("<b>[NATTAYARAAT]</b>", styles["company_name"])
    else:
        logo_img = Paragraph(f"<b>{COMPANY.get('short_name', 'NTT')}</b>", styles["company_name"])

    addr_html = (
        f"<b>{COMPANY.get('name', '')}</b><br/>"
        f"{COMPANY.get('address_line1', '')}<br/>"
        f"{COMPANY.get('address_line2', '')} {COMPANY.get('address_line3', '')}<br/>"
        f"Tax ID: {COMPANY.get('tax_id', '')} · Tel: {COMPANY.get('tel', '')} · Email: {COMPANY.get('email', '')}"
    )
    from pdf.bl_document_renderer import resolve_document_title
    doc_title = resolve_document_title(payload_or_bl=bl_doc, job=job_doc, booking=booking_doc)
    title_text = doc_title
    if doc_title == "AIR WAYBILL":
        type_text = f"HOUSE AIR WAYBILL ({bl_no})" if bl_type == "HBL" else f"MASTER AIR WAYBILL ({bl_no})"
    elif doc_title == "TRUCK WAYBILL":
        type_text = f"HOUSE TRUCK WAYBILL ({bl_no})" if bl_type == "HBL" else f"MASTER TRUCK WAYBILL ({bl_no})"
    else:
        type_text = f"HOUSE BILL OF LADING ({bl_no})" if bl_type == "HBL" else f"MASTER BILL OF LADING ({bl_no})"

    title_block = [
        Paragraph(title_text, styles["doc_title"]),
        Paragraph(type_text, styles["doc_subtitle"]),
    ]

    header_tbl = Table([[logo_img, comp_block, title_block]], colWidths=[40*mm, 85*mm, 61*mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 2*mm))

    # ---------------------------------------------------------
    # 2. STATUS BANNER / WATERMARK
    # ---------------------------------------------------------
    banner_bg = BRAND_BLUE
    banner_text = f"DOCUMENT STATUS: {status.upper()}"

    if status.lower() == "draft":
        banner_bg = colors.HexColor("#64748B")
        banner_text = "DRAFT — NOT FOR SHIPPING OR NEGOTIATION"
    elif status.lower() == "submitted":
        banner_bg = colors.HexColor("#0284C7")
        banner_text = "SUBMITTED — PENDING APPROVAL"
    elif status.lower() == "approved":
        banner_bg = colors.HexColor("#D97706")
        banner_text = "APPROVED — READY FOR ISSUANCE"
    elif status.lower() in ("issued", "released"):
        banner_bg = BRAND_NAVY
        banner_text = "ORIGINAL BILL OF LADING — NON-NEGOTIABLE UNLESS ENDORSED"
    elif status.lower() == "surrendered":
        banner_bg = colors.HexColor("#B91C1C")
        banner_text = "EXPRESS RELEASE / CARGO SURRENDERED"
    elif status.lower() == "cancelled":
        banner_bg = STATUS_RED
        banner_text = "CANCELLED DOCUMENT — VOID"

    banner_tbl = Table([[Paragraph(banner_text, styles["status_banner"])]], colWidths=[186*mm])
    banner_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), banner_bg),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(banner_tbl)
    story.append(Spacer(1, 3*mm))

    # ---------------------------------------------------------
    # 3. PARTIES SECTION (SHIPPER, CONSIGNEE, NOTIFY)
    # ---------------------------------------------------------
    shipper_val = _clean_str(bl.get("shipper")) or _clean_str(job.get("shipper")) or "—"
    consignee_val = _clean_str(bl.get("consignee")) or _clean_str(job.get("consignee")) or "—"
    notify_val = _clean_str(bl.get("notify_party")) or _clean_str(job.get("notify_party")) or "SAME AS CONSIGNEE"

    shipper_box = [
        Table([[Paragraph("<b>SHIPPER / EXPORTER</b>", styles["box_header"])]], colWidths=[91*mm],
              style=[("BACKGROUND", (0,0), (-1,-1), BRAND_BLUE), ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2)]),
        Spacer(1, 1*mm),
        Paragraph(shipper_val.replace("\n", "<br/>"), styles["value_text"]),
    ]

    consignee_box = [
        Table([[Paragraph("<b>CONSIGNEE (IF 'TO ORDER' STATE)</b>", styles["box_header"])]], colWidths=[91*mm],
              style=[("BACKGROUND", (0,0), (-1,-1), BRAND_BLUE), ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2)]),
        Spacer(1, 1*mm),
        Paragraph(consignee_val.replace("\n", "<br/>"), styles["value_text"]),
    ]

    parties_top_tbl = Table([[shipper_box, consignee_box]], colWidths=[93*mm, 93*mm])
    parties_top_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ]))
    story.append(parties_top_tbl)
    story.append(Spacer(1, 2*mm))

    notify_box = [
        Table([[Paragraph("<b>NOTIFY PARTY</b>", styles["box_header"])]], colWidths=[184*mm],
              style=[("BACKGROUND", (0,0), (-1,-1), BRAND_NAVY), ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2)]),
        Spacer(1, 1*mm),
        Paragraph(notify_val.replace("\n", "<br/>"), styles["value_text"]),
    ]
    notify_tbl = Table([[notify_box]], colWidths=[186*mm])
    notify_tbl.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 2)]))
    story.append(notify_tbl)
    story.append(Spacer(1, 3*mm))

    # ---------------------------------------------------------
    # 4. ROUTING & VESSEL TRANSPORT MATRIX
    # ---------------------------------------------------------
    por_val = _clean_str(bl.get("place_of_receipt")) or _clean_str(bl.get("por")) or _clean_str(job.get("place_of_receipt")) or _clean_str(job.get("por")) or "—"
    pol_val = _clean_str(bl.get("port_of_loading")) or _clean_str(bl.get("pol")) or _clean_str(job.get("pol")) or "—"
    pod_val = _clean_str(bl.get("port_of_discharge")) or _clean_str(bl.get("pod")) or _clean_str(job.get("pod")) or "—"
    deliv_val = _clean_str(bl.get("place_of_delivery")) or _clean_str(bl.get("final_destination")) or _clean_str(job.get("final_destination")) or "—"
    tranship_val = _clean_str(bl.get("transshipment_port")) or _clean_str(job.get("transshipment_port")) or "DIRECT"

    vessel_val = _clean_str(bl.get("vessel")) or _clean_str(job.get("vessel")) or "—"
    voyage_val = _clean_str(bl.get("voyage")) or _clean_str(job.get("voyage")) or "—"
    carrier_val = _clean_str(bl.get("carrier")) or _clean_str(job.get("carrier")) or "—"
    etd_val = _fmt_date(bl.get("etd") or job.get("etd")) or "—"
    eta_val = _fmt_date(bl.get("eta") or job.get("eta")) or "—"

    routing_data = [
        [
            Paragraph("<b>Place of Receipt (POR)</b>", styles["label_bold"]),
            Paragraph(f": {por_val}", styles["value_text"]),
            Paragraph("<b>Port of Loading (POL)</b>", styles["label_bold"]),
            Paragraph(f": {pol_val}", styles["value_text"]),
        ],
        [
            Paragraph("<b>Port of Discharge (POD)</b>", styles["label_bold"]),
            Paragraph(f": {pod_val}", styles["value_text"]),
            Paragraph("<b>Place of Delivery</b>", styles["label_bold"]),
            Paragraph(f": {deliv_val}", styles["value_text"]),
        ],
        [
            Paragraph("<b>Vessel & Voyage</b>", styles["label_bold"]),
            Paragraph(f": {vessel_val} / {voyage_val}", styles["value_text"]),
            Paragraph("<b>Ocean Carrier</b>", styles["label_bold"]),
            Paragraph(f": {carrier_val}", styles["value_text"]),
        ],
        [
            Paragraph("<b>ETD (Departure)</b>", styles["label_bold"]),
            Paragraph(f": {etd_val}", styles["value_text"]),
            Paragraph("<b>ETA (Arrival)</b>", styles["label_bold"]),
            Paragraph(f": {eta_val}", styles["value_text"]),
        ],
    ]

    routing_tbl = Table(routing_data, colWidths=[38*mm, 55*mm, 38*mm, 55*mm])
    routing_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREY),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.HexColor("#F1F5F9")),
        ("BACKGROUND", (0,0), (-1,-1), BG_LIGHT_GREY),
    ]))
    story.append(routing_tbl)
    story.append(Spacer(1, 3*mm))

    # ---------------------------------------------------------
    # 5. CARGO SPECIFICATIONS & COMMERCIAL SUMMARY
    # ---------------------------------------------------------
    freight_term = _clean_str(bl.get("freight_term")) or _clean_str(job.get("freight_term")) or "PREPAID"
    freight_payable = _clean_str(bl.get("freight_payable_at"), "ORIGIN PORT" if freight_term == "PREPAID" else "DESTINATION PORT")
    
    pkg_qty = _clean_str(bl.get("package_qty") or bl.get("package_quantity") or job.get("package_quantity"))
    pkg_type = _clean_str(bl.get("package_type") or job.get("package_type"), "PACKAGES")
    pkg_str = f"{pkg_qty} {pkg_type}" if pkg_qty else "1 SHIPMENT"

    gw_str = _fmt_num(bl.get("gross_weight") or job.get("gross_weight"), precision=2, unit="KG") or "—"
    cbm_str = _fmt_num(bl.get("measurement_cbm") or job.get("cbm"), precision=3, unit="CBM") or "—"
    commodity_str = _clean_str(bl.get("description_of_goods")) or _clean_str(job.get("commodity")) or "SAID TO CONTAIN GENERAL CARGO"

    cargo_headers = [
        [Paragraph("<b>Marks & Numbers</b>", styles["box_header"]),
         Paragraph("<b>No. of Pkgs</b>", styles["box_header"]),
         Paragraph("<b>Description of Goods & Cargo</b>", styles["box_header"]),
         Paragraph("<b>Gross Weight</b>", styles["box_header"]),
         Paragraph("<b>Measurement</b>", styles["box_header"])]
    ]
    cargo_head_tbl = Table(cargo_headers, colWidths=[35*mm, 25*mm, 75*mm, 26*mm, 25*mm])
    cargo_head_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BRAND_BLUE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(cargo_head_tbl)

    marks_val = _clean_str(bl.get("marks_numbers"), "N/M")
    hs_code_val = _clean_str(bl.get("hs_code"))
    desc_full = commodity_str
    if hs_code_val:
        desc_full += f"<br/><b>HS CODE:</b> {hs_code_val}"

    cargo_body = [
        [Paragraph(marks_val.replace("\n", "<br/>"), styles["value_text_small"]),
         Paragraph(pkg_str, styles["value_text_small"]),
         Paragraph(desc_full.replace("\n", "<br/>"), styles["value_text_small"]),
         Paragraph(gw_str, styles["value_text_small"]),
         Paragraph(cbm_str, styles["value_text_small"])]
    ]
    cargo_body_tbl = Table(cargo_body, colWidths=[35*mm, 25*mm, 75*mm, 26*mm, 25*mm])
    cargo_body_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREY),
    ]))
    story.append(cargo_body_tbl)
    story.append(Spacer(1, 3*mm))

    # ---------------------------------------------------------
    # 6. CONTAINER MANIFEST TABLE (FROM PHYSICAL JOB CONTAINERS)
    # ---------------------------------------------------------
    story.append(Paragraph("<b>CONTAINER & SEAL MANIFEST (PARTICULARS FURNISHED BY SHIPPER)</b>", styles["label_bold"]))
    story.append(Spacer(1, 1*mm))

    manifest_headers = [
        [Paragraph("Container No.", styles["manifest_head"]),
         Paragraph("Type / Size", styles["manifest_head"]),
         Paragraph("Seal No.", styles["manifest_head"]),
         Paragraph("Tare (KG)", styles["manifest_head"]),
         Paragraph("VGM (KG)", styles["manifest_head"]),
         Paragraph("Gross (KG)", styles["manifest_head"])]
    ]

    manifest_rows = []
    if containers:
        for c in containers:
            c_no = _clean_str(c.get("container_no"), "—")
            c_type = f"{_clean_str(c.get('container_size'))} {_clean_str(c.get('container_type'))}".strip() or "—"
            c_seal = _clean_str(c.get("seal_no"), "—")
            c_tare = _fmt_num(c.get("tare_weight"), precision=0) or "—"
            c_vgm = _fmt_num(c.get("vgm_kg"), precision=0) or "—"
            c_gross = _fmt_num(c.get("gross_weight"), precision=0) or "—"

            manifest_rows.append([
                Paragraph(c_no, styles["manifest_cell"]),
                Paragraph(c_type, styles["manifest_cell"]),
                Paragraph(c_seal, styles["manifest_cell"]),
                Paragraph(c_tare, styles["manifest_cell"]),
                Paragraph(c_vgm, styles["manifest_cell"]),
                Paragraph(c_gross, styles["manifest_cell"]),
            ])
    else:
        # Fallback if no container linked yet
        cnt_summary = _clean_str(bl.get("container_summary")) or _clean_str(job.get("cargo_type")) or "SHIPMENT CONSOLIDATED"
        manifest_rows.append([
            Paragraph(cnt_summary, styles["manifest_cell"]),
            Paragraph("—", styles["manifest_cell"]),
            Paragraph("—", styles["manifest_cell"]),
            Paragraph("—", styles["manifest_cell"]),
            Paragraph("—", styles["manifest_cell"]),
            Paragraph("—", styles["manifest_cell"]),
        ])

    manifest_table_data = manifest_headers + manifest_rows
    manifest_tbl = Table(manifest_table_data, colWidths=[40*mm, 30*mm, 35*mm, 27*mm, 27*mm, 27*mm], repeatRows=1)
    manifest_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BRAND_NAVY),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREY),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.HexColor("#E2E8F0")),
    ]))
    story.append(manifest_tbl)
    story.append(Spacer(1, 3*mm))

    # ---------------------------------------------------------
    # 7. SPECIAL INSTRUCTIONS & COMMERCIAL TERMS
    # ---------------------------------------------------------
    remarks_val = _clean_str(bl.get("remarks")) or _clean_str(bl.get("special_instructions")) or _clean_str(job.get("remark"))
    if remarks_val:
        story.append(Paragraph("<b>SPECIAL INSTRUCTIONS / REMARKS:</b>", styles["label_bold"]))
        story.append(Paragraph(remarks_val.replace("\n", "<br/>"), styles["value_text"]))
        story.append(Spacer(1, 3*mm))

    # ---------------------------------------------------------
    # 8. FOOTER, ISSUANCE & SIGNATURE BLOCK
    # ---------------------------------------------------------
    num_orig = _clean_str(bl.get("number_of_originals"), "THREE (3)")
    place_issue = _clean_str(bl.get("place_of_issue"), "BANGKOK, THAILAND")
    date_issue = _fmt_date(bl.get("bl_date") or bl.get("created_at")) or _fmt_date(date.today())

    footer_data = [
        [
            Paragraph(f"<b>Freight Term:</b> {freight_term}<br/><b>Payable At:</b> {freight_payable}", styles["value_text_small"]),
            Paragraph(f"<b>No. of Originals:</b> {num_orig}<br/><b>Place of Issue:</b> {place_issue}", styles["value_text_small"]),
            Paragraph(f"<b>Date of Issue:</b> {date_issue}<br/><b>Ref Job:</b> {job.get('job_no', '—')}", styles["value_text_small"]),
        ]
    ]
    footer_info_tbl = Table(footer_data, colWidths=[62*mm, 62*mm, 62*mm])
    footer_info_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER_GREY),
        ("BACKGROUND", (0,0), (-1,-1), BG_LIGHT_GREY),
    ]))
    story.append(footer_info_tbl)
    story.append(Spacer(1, 3*mm))

    # Signature Block
    sig_content = [
        [
            Paragraph("<b>FOR AND ON BEHALF OF THE CARRIER / AGENT</b><br/>"
                      f"<b>{COMPANY.get('name', '')}</b>", styles["value_text_small"]),
            Paragraph("<b>AUTHORIZED SIGNATURE</b>", styles["value_text_small"]),
        ],
        [
            Spacer(1, 14*mm),
            Spacer(1, 14*mm),
        ],
        [
            Paragraph(f"_______________________________________<br/><b>{COMPANY.get('signer_name', '')}</b><br/>{COMPANY.get('signer_title', '')}", styles["value_text_small"]),
            Paragraph("_______________________________________<br/>As Agent for the Carrier", styles["value_text_small"]),
        ]
    ]
    sig_tbl = Table(sig_content, colWidths=[93*mm, 93*mm])
    sig_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
    ]))
    story.append(KeepTogether(sig_tbl))

    # Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
