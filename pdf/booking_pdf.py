"""Modern Booking Confirmation PDF.
Canonical wording: Booking Confirmation, Carrier, Vessel / Voyage, Mother Vessel.
Phase 30: transport-specific cargo/equipment and CY/CFS presentation.
"""
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD
from core.freight_rules import get_freight_profile

BLUE = colors.HexColor('#1F4E9E')
GOLD = colors.HexColor('#C9A227')
LIGHT = colors.HexColor('#F5F8FC')


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


def _s(v, default='—'):
    if v is None:
        return default
    x = _clean_text(v)
    return default if not x or x.lower() in {'none', 'nan', 'nat'} else x


def _fmt(v):
    if not v:
        return '—'
    try:
        return datetime.strptime(str(v)[:10], '%Y-%m-%d').strftime('%d-%b-%Y')
    except Exception:
        return _s(v)


def _mode(booking: Dict[str, Any]) -> str:
    return get_freight_profile(booking.get('mode') or booking.get('job_type'), booking.get('cargo_type')).transport


def _cargo_type(booking: Dict[str, Any]) -> str:
    return get_freight_profile(booking.get('mode') or booking.get('job_type'), booking.get('cargo_type')).cargo_type


def _is_sea_fcl(booking: Dict[str, Any]) -> bool:
    profile = get_freight_profile(booking.get('mode') or booking.get('job_type'), booking.get('cargo_type'))
    return profile.volume_kind == 'CONTAINER' and profile.receiving_kind == 'CY'


def _parse_equipment_summary(booking: Dict[str, Any]):
    rows = []
    ctype = _s(booking.get('container_type'), '').strip()
    qty = booking.get('container_quantity') or booking.get('quantity')
    if ctype and qty:
        try:
            rows.append((ctype, int(float(qty))))
        except (TypeError, ValueError):
            rows.append((ctype, _s(qty)))
    summary = _s(booking.get('container_summary'), '').strip()
    if summary and summary != '—':
        for match in re.finditer(r'(\d+)\s*[xX×]\s*([0-9\'A-Za-z\-]+)', summary):
            parsed_qty = int(match.group(1))
            parsed_type = match.group(2).replace('HC', "'HC").replace('GP', "'GP")
            if (parsed_type, parsed_qty) not in rows:
                rows.append((parsed_type, parsed_qty))
    if not rows and summary and summary != '—':
        rows.append((summary, _s(qty, '')))
    return rows


def _styles():
    base = getSampleStyleSheet()
    return {
        'company': ParagraphStyle('company', parent=base['Normal'], fontName=THAI_FONT_BOLD, fontSize=18, textColor=GOLD, leading=22, spaceAfter=6),
        'addr': ParagraphStyle('addr', parent=base['Normal'], fontName=THAI_FONT, fontSize=8.5, textColor=BLUE, leading=12),
        'title': ParagraphStyle('title', parent=base['Normal'], fontName=THAI_FONT_BOLD, fontSize=18, textColor=BLUE, alignment=TA_CENTER, spaceBefore=5, spaceAfter=9),
        'label': ParagraphStyle('label', parent=base['Normal'], fontName=THAI_FONT_BOLD, fontSize=8.5, leading=11),
        'value': ParagraphStyle('value', parent=base['Normal'], fontName=THAI_FONT, fontSize=8.5, leading=11),
        'body': ParagraphStyle('body', parent=base['Normal'], fontName=THAI_FONT, fontSize=8.5, leading=12),
        'watermark': ParagraphStyle('watermark', parent=base['Normal'], fontName=THAI_FONT_BOLD, fontSize=42, textColor=colors.Color(0.75, 0.75, 0.75, alpha=0.22), alignment=TA_CENTER),
    }


def _header(styles):
    logo_path = COMPANY.get('logo_path')
    logo = Paragraph('', styles['body'])
    if logo_path and Path(logo_path).exists():
        logo = Image(logo_path, width=35 * mm, height=22 * mm)
    addr = f"{COMPANY['address_line1']}<br/>{COMPANY['address_line2']}<br/>{COMPANY['address_line3']}<br/>Tax ID {COMPANY['tax_id']} · Tel {COMPANY['tel']} · Email {COMPANY['email']}"
    company = [Paragraph(COMPANY['name'], styles['company']), Paragraph(addr, styles['addr'])]
    t = Table([[logo, company]], colWidths=[40 * mm, 140 * mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def _grid(rows, styles, header=None, color=LIGHT):
    data = []
    if header:
        data.append([Paragraph(f'<b>{header}</b>', styles['label']), '', '', ''])
    for a, b, c, d in rows:
        data.append([
            Paragraph(f'<b>{a}</b>', styles['label']),
            Paragraph(_s(b), styles['value']),
            Paragraph(f'<b>{c}</b>', styles['label']),
            Paragraph(_s(d), styles['value']),
        ])
    t = Table(data, colWidths=[39 * mm, 51 * mm, 39 * mm, 51 * mm])
    cmd = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), .5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.lightgrey),
    ]
    if header:
        cmd += [
            ('SPAN', (0, 0), (-1, 0)),
            ('BACKGROUND', (0, 0), (-1, 0), color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ]
    t.setStyle(TableStyle(cmd))
    return t


def _watermark(canvas, doc, approval_status):
    canvas.saveState()
    canvas.setFont(THAI_FONT, 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f'Page {doc.page}')
    canvas.restoreState()


def generate_booking_pdf(booking: Any, output_path: str = None, approval_status: str = 'Draft') -> str:
    if isinstance(booking, str):
        from managers.booking_manager import get_booking
        b_doc = get_booking(booking)
        if not b_doc:
            raise ValueError(f"Booking '{booking}' not found.")
        booking = b_doc
    bno = _s(booking.get('booking_no'), 'BOOKING')
    if output_path is None:
        output_path = str(Path(OUTPUT_DIR) / f'BC_{bno}.pdf')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=18 * mm, title=f'Booking Confirmation {bno}', author=COMPANY['name'])
    stl = _styles()
    story = [_header(stl), Spacer(1, 4 * mm), Paragraph('BOOKING CONFIRMATION', stl['title'])]

    story += [_grid([
        ('Booking No.', booking.get('booking_no'), 'Carrier Booking No.', booking.get('carrier_booking_no')),
        ('Booking Date', _fmt(booking.get('booking_date')), 'Customer', booking.get('customer_name')),
        ('Shipper', booking.get('shipper'), 'Consignee', booking.get('consignee')),
        ('ETD', _fmt(booking.get('etd')), 'ETA', _fmt(booking.get('eta'))),
    ], stl, header='Booking Details', color=BLUE), Spacer(1, 4 * mm)]

    vessel_name = _s(booking.get('vessel') or booking.get('feeder_vessel') or booking.get('m_vessel') or booking.get('mother_vessel'))
    vessel_voyage = vessel_name if vessel_name == '—' else f"{vessel_name} / {_s(booking.get('voyage') or booking.get('feeder_voyage'))}".strip(' /')
    mv_name = _s(booking.get('mother_vessel') or booking.get('m_vessel'))
    mv_voy = _s(booking.get('mother_voyage') or booking.get('m_voyage'))
    mother_vessel = mv_name if mv_name == '—' else (f"{mv_name} / {mv_voy}".strip(' /') if mv_voy else mv_name)
    story += [_grid([
        ('POL', booking.get('pol'), 'POR', booking.get('por')),
        ('Transshipment Port', booking.get('transhipment_port'), 'POD', booking.get('pod')),
        ('Carrier', booking.get('carrier'), 'Vessel / Voyage', vessel_voyage),
        ('Mother Vessel', mother_vessel, 'Final Destination', booking.get('final_destination')),
    ], stl, header='Routing & Vessel', color=BLUE), Spacer(1, 4 * mm)]

    profile = get_freight_profile(booking.get('mode') or booking.get('job_type'), booking.get('cargo_type'))
    if profile.volume_kind == 'CONTAINER':
        equipment_rows = _parse_equipment_summary(booking)
        cargo_rows = []
        if equipment_rows:
            for idx, (ctype, qty) in enumerate(equipment_rows):
                cargo_rows.append(('Container Type' if idx == 0 else '', ctype, 'Quantity' if idx == 0 else '', qty))
        else:
            cargo_rows.append(('Equipment', booking.get('container_summary'), 'Quantity', booking.get('quantity') or booking.get('container_quantity')))
        story += [_grid(cargo_rows, stl, header='Cargo & Equipment', color=BLUE), Spacer(1, 4 * mm)]
    elif profile.volume_kind == 'KG':
        story += [_grid([
            ('Packages', f"{_s(booking.get('package_qty'), '0')} {_s(booking.get('package_unit'), 'PKGS')}", 'Gross Weight', f"{_s(booking.get('gross_weight'), '0')} KG"),
            ('Chargeable Weight', f"{_s(booking.get('chargeable_weight'), '—')} KG", 'Commodity', booking.get('commodity')),
        ], stl, header='Cargo Details', color=BLUE), Spacer(1, 4 * mm)]
    elif profile.volume_kind == 'TRUCK':
        story += [_grid([
            ('Truck Type', booking.get('truck_type') or booking.get('container_summary'), 'Quantity', booking.get('quantity') or booking.get('truck_quantity')),
            ('Commodity', booking.get('commodity'), 'Gross Weight', f"{_s(booking.get('gross_weight'), '0')} KG"),
        ], stl, header='Transport Equipment', color=BLUE), Spacer(1, 4 * mm)]
    else:
        story += [_grid([
            ('Packages', f"{_s(booking.get('package_qty'), '0')} {_s(booking.get('package_unit'), 'PKGS')}", 'Gross Weight', f"{_s(booking.get('gross_weight'), '0')} KG"),
            ('Volume', f"{_s(booking.get('measurement_cbm'), '0')} CBM", 'Commodity', booking.get('commodity')),
        ], stl, header='Cargo Details', color=BLUE), Spacer(1, 4 * mm)]

    if profile.show_cy:
        story += [_grid([
            ('CY Date', _fmt(booking.get('cy_date')), 'CY Place', booking.get('cy_place')),
            ('Container Return Date', _fmt(booking.get('customer_return_date')), 'Return Place', booking.get('return_place')),
        ], stl, header='CY / Container Schedule', color=GOLD), Spacer(1, 4 * mm)]
    elif profile.show_cfs:
        story += [_grid([('CFS Date', _fmt(booking.get('cfs_date')), 'CFS Place', booking.get('cfs_place'))], stl, header='CFS Receiving', color=GOLD), Spacer(1, 4 * mm)]

    remark = _s(booking.get('remark'), '')
    if remark:
        story += [Paragraph('<b>Remarks</b>', stl['label']), Paragraph(remark.replace('\n', '<br/>'), stl['body']), Spacer(1, 4 * mm)]

    sig = Table([[Paragraph('Yours sincerely,', stl['body']), Paragraph('_' * 30, stl['body'])], [Spacer(1, 14 * mm), Paragraph(f"<b>{COMPANY['signer_name']}</b><br/>{COMPANY['signer_title']}", stl['body'])]], colWidths=[90 * mm, 90 * mm])
    sig.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    story += [Spacer(1, 7 * mm), sig]
    doc.build(story, onFirstPage=lambda c, d: _watermark(c, d, approval_status), onLaterPages=lambda c, d: _watermark(c, d, approval_status))
    return output_path


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(THAI_FONT, 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f'Page {doc.page}')
    canvas.restoreState()
