"""Shipping Instruction (S/I) PDF Generator.

Enterprise freight forwarding format for submitting Shipping Instructions
to Ocean Carriers / Shipping Lines for Master B/L issuance:
- Supports both Direct B/L mode and Agent B/L (HBL Mode).
- Complete routing, vessel, carrier booking, and carrier MBL details.
- Comprehensive parties block (Shipper, Consignee, Notify Party, Delivery Agent).
- Container & Seal manifest with packages, weights, and measurements.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.utils import ImageReader

from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

NAVY_PRIMARY = colors.HexColor("#0F294A")
BLUE_PRIMARY = colors.HexColor("#1D4ED8")
BLUE_LIGHT = colors.HexColor("#F0F7FF")
BORDER_BLUE = colors.HexColor("#3B82F6")
BORDER_LIGHT = colors.HexColor("#CBD5E1")
TEXT_DARK = colors.HexColor("#0F172A")
HEADER_BG = colors.HexColor("#1E293B")
SUB_HEADER_BG = colors.HexColor("#F1F5F9")
GREEN_ACCENT = colors.HexColor("#15803D")


def _s(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if not text or text.lower() in {"none", "nan", "nat"} else text


def _styles():
    base = getSampleStyleSheet()
    return {
        "company_th": ParagraphStyle("si_comp_th", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=10, leading=12.5, textColor=NAVY_PRIMARY),
        "company_en": ParagraphStyle("si_comp_en", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=11, textColor=NAVY_PRIMARY),
        "company_addr": ParagraphStyle("si_comp_addr", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.0, leading=9.2, textColor=TEXT_DARK),
        
        "title": ParagraphStyle("si_title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=13.0, leading=15, textColor=NAVY_PRIMARY, alignment=TA_RIGHT),
        "subtitle": ParagraphStyle("si_subtitle", parent=base["Normal"], fontName=THAI_FONT, fontSize=8.0, leading=10, textColor=BLUE_PRIMARY, alignment=TA_RIGHT),
        "badge_hbl": ParagraphStyle("si_badge_hbl", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=10.5, textColor=colors.HexColor("#B91C1C"), alignment=TA_RIGHT),
        "badge_dir": ParagraphStyle("si_badge_dir", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=10.5, textColor=GREEN_ACCENT, alignment=TA_RIGHT),
        
        "sec_title": ParagraphStyle("si_sec_title", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.8, leading=10, textColor=colors.white),
        "th_center": ParagraphStyle("si_th_center", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.0, leading=9.0, alignment=TA_CENTER, textColor=TEXT_DARK),
        "th_left": ParagraphStyle("si_th_left", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.0, leading=9.0, alignment=TA_LEFT, textColor=TEXT_DARK),
        "th_right": ParagraphStyle("si_th_right", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.0, leading=9.0, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "label": ParagraphStyle("si_label", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.0, leading=9.0, textColor=TEXT_DARK),
        "value": ParagraphStyle("si_value", parent=base["Normal"], fontName=THAI_FONT, fontSize=7.0, leading=9.0, textColor=TEXT_DARK),
        "value_b": ParagraphStyle("si_value_b", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.2, leading=9.2, textColor=NAVY_PRIMARY),
        
        "party_head": ParagraphStyle("si_party_head", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.5, leading=9.5, textColor=NAVY_PRIMARY),
        "party_text": ParagraphStyle("si_party_text", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, textColor=TEXT_DARK),
        
        "td_center": ParagraphStyle("si_td_center", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_CENTER, textColor=TEXT_DARK),
        "td_left": ParagraphStyle("si_td_left", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_LEFT, textColor=TEXT_DARK),
        "td_right": ParagraphStyle("si_td_right", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.8, leading=8.8, alignment=TA_RIGHT, textColor=TEXT_DARK),
        
        "sign_role": ParagraphStyle("si_sign_role", parent=base["Normal"], fontName=THAI_FONT_BOLD, fontSize=7.0, leading=9.0, alignment=TA_CENTER, textColor=TEXT_DARK),
        "sign_text": ParagraphStyle("si_sign_text", parent=base["Normal"], fontName=THAI_FONT, fontSize=6.5, leading=8.2, alignment=TA_CENTER, textColor=TEXT_DARK),
    }


def _header(payload: Dict[str, Any], styles) -> Table:
    logo_path = COMPANY.get("logo_path")
    logo = None
    if logo_path and Path(str(logo_path)).exists():
        try:
            ir = ImageReader(str(logo_path))
            iw, ih = ir.getSize()
            scale = min(32 * mm / iw, 17 * mm / ih)
            logo = Image(str(logo_path), width=iw * scale, height=ih * scale)
        except Exception:
            logo = None
    if logo is None:
        logo = Paragraph("<b>NATTAYAARAT</b>", styles["company_th"])

    comp_th = "บริษัท ณัฐยาราชย์ จำกัด (สำนักงานใหญ่)"
    comp_en = "NATTAYAARAT CO.,LTD. (Head Office)"
    addr_line = "เลขที่ 59/9 หมู่ที่ 4 ตำบลบางกระทึก อำเภอสามพราน จังหวัดนครปฐม 73210"
    tax_tel = f"TAX ID: {COMPANY.get('tax_id', '0735568004823')} | โทร: {COMPANY.get('tel', '')}"

    comp_block = [
        Paragraph(f"<b>{comp_th}</b>", styles["company_th"]),
        Paragraph(f"<b>{comp_en}</b>", styles["company_en"]),
        Paragraph(addr_line, styles["company_addr"]),
        Paragraph(tax_tel, styles["company_addr"]),
    ]

    is_hbl = payload.get("si_mode") == "hbl"
    badge_style = styles["badge_hbl"] if is_hbl else styles["badge_dir"]
    badge_label = f"[{payload.get('si_mode_label', 'DIRECT B/L')}]"

    title_block = [
        Paragraph(f"<b>{badge_label}</b>", badge_style),
        Spacer(1, 1 * mm),
        Paragraph("<b>SHIPPING INSTRUCTION (S/I)</b>", styles["title"]),
        Paragraph("เอกสารแจ้งรายละเอียดเพื่อออกใบตราส่งสินค้า (Master B/L)", styles["subtitle"]),
    ]

    tbl = Table([[logo, comp_block, title_block]], colWidths=[34 * mm, 80 * mm, 68 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 3),
    ]))
    return tbl


def _booking_grid(payload: Dict[str, Any], styles) -> Table:
    vessel_str = f"{_s(payload.get('vessel'))} {_s(payload.get('voyage'))}".strip()
    mv_str = f"{_s(payload.get('mother_vessel'))} {_s(payload.get('mother_voyage'))}".strip()

    si_date_str = str(payload.get("si_date") or date.today())
    if len(si_date_str) >= 10:
        try:
            si_date_str = datetime.strptime(si_date_str[:10], "%Y-%m-%d").strftime("%d-%b-%Y")
        except Exception:
            pass

    rows = [
        [
            Paragraph("<b>Job No. / Ref.</b>", styles["label"]),
            Paragraph(f"<b>{_s(payload.get('job_no'))}</b>", styles["value_b"]),
            Paragraph("<b>Date of S/I</b>", styles["label"]),
            Paragraph(si_date_str, styles["value"]),
            Paragraph("<b>Freight Term</b>", styles["label"]),
            Paragraph(f"<b>{_s(payload.get('freight_term'), 'PREPAID')}</b>", styles["value_b"]),
        ],
        [
            Paragraph("<b>Carrier (สายเรือ)</b>", styles["label"]),
            Paragraph(f"<b>{_s(payload.get('carrier'))}</b>", styles["value_b"]),
            Paragraph("<b>Carrier Booking No.</b>", styles["label"]),
            Paragraph(f"<b>{_s(payload.get('carrier_booking_no'))}</b>", styles["value_b"]),
            Paragraph("<b>Carrier MBL No.</b>", styles["label"]),
            Paragraph(_s(payload.get("carrier_mbl_no")), styles["value"]),
        ],
        [
            Paragraph("<b>Feeder / Ocean Vessel</b>", styles["label"]),
            Paragraph(vessel_str if vessel_str != "—" else "—", styles["value"]),
            Paragraph("<b>Mother Vessel / Voy</b>", styles["label"]),
            Paragraph(mv_str if mv_str != "—" else "—", styles["value"]),
            Paragraph("<b>Company HBL No.</b>", styles["label"]),
            Paragraph(_s(payload.get("hbl_no")), styles["value"]),
        ],
        [
            Paragraph("<b>Port of Loading (POL)</b>", styles["label"]),
            Paragraph(f"<b>{_s(payload.get('pol'))}</b>", styles["value_b"]),
            Paragraph("<b>Port of Discharge (POD)</b>", styles["label"]),
            Paragraph(f"<b>{_s(payload.get('pod'))}</b>", styles["value_b"]),
            Paragraph("<b>Transshipment Port</b>", styles["label"]),
            Paragraph(_s(payload.get("transshipment")), styles["value"]),
        ],
        [
            Paragraph("<b>Place of Receipt</b>", styles["label"]),
            Paragraph(_s(payload.get("place_of_receipt")), styles["value"]),
            Paragraph("<b>Place of Delivery</b>", styles["label"]),
            Paragraph(_s(payload.get("place_of_delivery")), styles["value"]),
            Paragraph("<b>ETD / ETA</b>", styles["label"]),
            Paragraph(f"{_s(payload.get('etd'))} / {_s(payload.get('eta'))}", styles["value"]),
        ],
    ]

    tbl = Table(rows, colWidths=[28 * mm, 44 * mm, 28 * mm, 44 * mm, 20 * mm, 18 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER_LIGHT),
    ]))
    return tbl


def _parties_section(payload: Dict[str, Any], styles) -> Table:
    def _format_lines(text: str) -> List[Paragraph]:
        res = []
        for line in str(text or "").split("\n"):
            l = line.strip()
            if l:
                res.append(Paragraph(l, styles["party_text"]))
        return res or [Paragraph("—", styles["party_text"])]

    box_shipper = [
        Paragraph("<b>1. SHIPPER (ผู้ส่งสินค้าบน MBL)</b>", styles["party_head"]),
        Spacer(1, 1 * mm),
    ] + _format_lines(payload.get("shipper"))

    box_consignee = [
        Paragraph("<b>2. CONSIGNEE (ผู้รับสินค้าบน MBL)</b>", styles["party_head"]),
        Spacer(1, 1 * mm),
    ] + _format_lines(payload.get("consignee"))

    box_notify = [
        Paragraph("<b>3. NOTIFY PARTY (ผู้รับแจ้งเตือน)</b>", styles["party_head"]),
        Spacer(1, 1 * mm),
    ] + _format_lines(payload.get("notify_party"))

    box_agent = [
        Paragraph("<b>4. FOR DELIVERY / AGENT (Agent ปลายทาง)</b>", styles["party_head"]),
        Spacer(1, 1 * mm),
    ] + _format_lines(payload.get("delivery_agent") or "SAME AS CONSIGNEE")

    tbl = Table(
        [[box_shipper, box_consignee], [box_notify, box_agent]],
        colWidths=[91 * mm, 91 * mm],
        rowHeights=[28 * mm, 24 * mm],
    )
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (0, 0), 0.6, BORDER_BLUE),
        ("BOX", (1, 0), (1, 0), 0.6, BORDER_BLUE),
        ("BOX", (0, 1), (0, 1), 0.6, BORDER_BLUE),
        ("BOX", (1, 1), (1, 1), 0.6, BORDER_BLUE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return tbl


def _manifest_table(payload: Dict[str, Any], styles) -> Table:
    headers = [
        Paragraph("<b>Container & Seal No. / Marks & Nos</b>", styles["th_left"]),
        Paragraph("<b>Quantity & Package</b>", styles["th_center"]),
        Paragraph("<b>Description of Goods</b>", styles["th_left"]),
        Paragraph("<b>Gross Weight</b>", styles["th_right"]),
        Paragraph("<b>Measurement</b>", styles["th_right"]),
    ]

    containers = list(payload.get("containers") or [])
    data = [headers]

    desc_main = _s(payload.get("commodity"))
    hs_str = f"HS CODE: {_s(payload.get('hs_code'))}" if payload.get("hs_code") else ""
    full_desc = f"{desc_main}<br/>{hs_str}".strip()

    if containers:
        for idx, ctr in enumerate(containers):
            ctr_no = _s(ctr.get("container_no") or ctr.get("container_number"))
            seal = _s(ctr.get("seal_no"))
            sz = _s(ctr.get("container_size") or ctr.get("container_type"))
            pkg = f"{_s(ctr.get('package_qty') or ctr.get('packages'))} {_s(ctr.get('package_type') or payload.get('package_type'))}".strip()
            gw = f"{float(ctr.get('gross_weight') or ctr.get('weight') or 0):,.2f} KGS"
            cbm = f"{float(ctr.get('volume_cbm') or ctr.get('cbm') or 0):,.3f} CBM"

            row = [
                Paragraph(f"<b>{ctr_no}</b> / SEAL: {seal}<br/>Size: {sz}", styles["td_left"]),
                Paragraph(pkg if pkg != "—" else f"{payload.get('package_qty')} {payload.get('package_type')}", styles["td_center"]),
                Paragraph(full_desc if idx == 0 else "SAID TO CONTAIN THE SAME", styles["td_left"]),
                Paragraph(gw, styles["td_right"]),
                Paragraph(cbm, styles["td_right"]),
            ]
            data.append(row)
    else:
        pkg_str = f"{payload.get('package_qty', 0)} {_s(payload.get('package_type'), 'PKGS')}"
        gw_str = f"{float(payload.get('gross_weight') or 0):,.2f} KGS"
        cbm_str = f"{float(payload.get('cbm') or 0):,.3f} CBM"
        data.append([
            Paragraph("N/M<br/>(AS PER ATTACHED MANIFEST)", styles["td_left"]),
            Paragraph(pkg_str, styles["td_center"]),
            Paragraph(full_desc, styles["td_left"]),
            Paragraph(gw_str, styles["td_right"]),
            Paragraph(cbm_str, styles["td_right"]),
        ])

    tbl = Table(data, colWidths=[48 * mm, 30 * mm, 56 * mm, 24 * mm, 24 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SUB_HEADER_BG),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, BORDER_BLUE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDER_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_LIGHT),
    ]))
    return tbl


def _footer_block(payload: Dict[str, Any], styles) -> Table:
    remarks_text = _s(payload.get("special_remarks"), "N/A")
    payable = _s(payload.get("freight_payable_at"), "BANGKOK, THAILAND")

    rem_box = [
        Paragraph("<b>SPECIAL INSTRUCTIONS & REMARKS :</b>", styles["label"]),
        Paragraph(f"• Freight Payable at: <b>{payable}</b>", styles["value"]),
        Paragraph(f"• Remarks: {remarks_text}", styles["value"]),
    ]

    prep_by = _s(payload.get("prepared_by"), "OPERATIONS")
    sign_box = [
        Paragraph("<b>PREPARED & SUBMITTED BY :</b>", styles["sign_role"]),
        Spacer(1, 10 * mm),
        Paragraph(f"<b>NATTAYAARAT CO., LTD.</b> ({prep_by})", styles["sign_text"]),
        Paragraph(f"Date: {date.today().strftime('%d-%b-%Y')}", styles["sign_text"]),
    ]

    tbl = Table([[rem_box, sign_box]], colWidths=[120 * mm, 62 * mm], rowHeights=[22 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (0, 0), 0.6, BORDER_LIGHT),
        ("BOX", (1, 0), (1, 0), 0.6, BORDER_LIGHT),
        ("BACKGROUND", (0, 0), (0, 0), BLUE_LIGHT),
        ("BACKGROUND", (1, 0), (1, 0), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return tbl


def generate_si_pdf(payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Generate official A4 Shipping Instruction (S/I) PDF."""
    job_no = _s(payload.get("job_no"), "JOB")
    mode = payload.get("si_mode", "direct")
    
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f"SI_{mode.upper()}_{job_no}.pdf")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"Shipping Instruction {job_no} ({payload.get('si_mode_label', mode)})",
        author=COMPANY.get("name", "NATTAYAARAT CO., LTD."),
    )

    styles = _styles()
    story = []

    story.append(_header(payload, styles))
    story.append(Spacer(1, 2.5 * mm))
    story.append(_booking_grid(payload, styles))
    story.append(Spacer(1, 2.5 * mm))
    story.append(_parties_section(payload, styles))
    story.append(Spacer(1, 2.5 * mm))
    story.append(_manifest_table(payload, styles))
    story.append(Spacer(1, 2.5 * mm))
    story.append(_footer_block(payload, styles))

    doc.build(story)
    return output_path
