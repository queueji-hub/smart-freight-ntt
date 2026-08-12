"""Modern Booking Confirmation PDF.
Canonical wording: Booking Confirmation, Carrier, Mother Vessel.
Revision metadata is intentionally not printed to users.
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from config import COMPANY, OUTPUT_DIR
from pdf.fonts import THAI_FONT, THAI_FONT_BOLD

BLUE=colors.HexColor('#1F4E9E'); GOLD=colors.HexColor('#C9A227'); LIGHT=colors.HexColor('#F5F8FC')

def _s(v, default='—'):
    if v is None: return default
    x=str(v).strip()
    return default if not x or x.lower() in {'none','nan','nat'} else x

def _fmt(v):
    if not v: return '—'
    try: return datetime.strptime(str(v)[:10],'%Y-%m-%d').strftime('%d-%b-%Y')
    except Exception: return _s(v)

def _styles():
    base=getSampleStyleSheet()
    return {
      'company':ParagraphStyle('company',parent=base['Normal'],fontName=THAI_FONT_BOLD,fontSize=18,textColor=GOLD,leading=22,spaceAfter=6),
      'addr':ParagraphStyle('addr',parent=base['Normal'],fontName=THAI_FONT,fontSize=8.5,textColor=BLUE,leading=12),
      'title':ParagraphStyle('title',parent=base['Normal'],fontName=THAI_FONT_BOLD,fontSize=18,textColor=BLUE,alignment=TA_CENTER,spaceBefore=5,spaceAfter=9),
      'label':ParagraphStyle('label',parent=base['Normal'],fontName=THAI_FONT_BOLD,fontSize=8.5,leading=11),
      'value':ParagraphStyle('value',parent=base['Normal'],fontName=THAI_FONT,fontSize=8.5,leading=11),
      'body':ParagraphStyle('body',parent=base['Normal'],fontName=THAI_FONT,fontSize=8.5,leading=12),
    }

def _header(styles):
    logo_path=COMPANY.get('logo_path')
    logo=Paragraph('',styles['body'])
    if logo_path and Path(logo_path).exists():
        logo=Image(logo_path,width=35*mm,height=22*mm)
    addr=f"{COMPANY['address_line1']}<br/>{COMPANY['address_line2']}<br/>{COMPANY['address_line3']}<br/>Tax ID {COMPANY['tax_id']} · Tel {COMPANY['tel']} · Email {COMPANY['email']}"
    company=[Paragraph(COMPANY['name'],styles['company']),Paragraph(addr,styles['addr'])]
    t=Table([[logo,company]],colWidths=[40*mm,140*mm]); t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0)])); return t

def _grid(rows,styles,header=None,color=LIGHT):
    data=[]
    if header: data.append([Paragraph(f'<b>{header}</b>',styles['label']),'','',''])
    for a,b,c,d in rows:
        data.append([Paragraph(f'<b>{a}</b>',styles['label']),Paragraph(_s(b),styles['value']),Paragraph(f'<b>{c}</b>',styles['label']),Paragraph(_s(d),styles['value'])])
    t=Table(data,colWidths=[39*mm,51*mm,39*mm,51*mm])
    cmd=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('BOX',(0,0),(-1,-1),.5,colors.grey),('INNERGRID',(0,0),(-1,-1),.25,colors.lightgrey)]
    if header:
        cmd += [('SPAN',(0,0),(-1,0)),('BACKGROUND',(0,0),(-1,0),color),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ALIGN',(0,0),(-1,0),'CENTER')]
    t.setStyle(TableStyle(cmd)); return t

def generate_booking_pdf(booking: Dict[str,Any], output_path: str=None) -> str:
    bno=_s(booking.get('booking_no'),'BOOKING')
    if output_path is None: output_path=str(Path(OUTPUT_DIR)/f'BC_{bno}.pdf')
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(output_path,pagesize=A4,leftMargin=15*mm,rightMargin=15*mm,topMargin=15*mm,bottomMargin=18*mm,title=f'Booking Confirmation {bno}',author=COMPANY['name'])
    stl=_styles(); story=[_header(stl),Spacer(1,4*mm),Paragraph('BOOKING CONFIRMATION',stl['title'])]
    story += [_grid([
      ('Booking No.',booking.get('booking_no'),'Customer',booking.get('customer_name')),
      ('Shipper',booking.get('shipper'),'Consignee',booking.get('consignee')),
      ('Notify Party',booking.get('notify_party'),'Job Type',booking.get('job_type')),
      ('Cargo Type',booking.get('cargo_type'),'Commodity',booking.get('commodity')),
      ('Weight',f"{_s(booking.get('gross_weight'),'0')} KG",'Measurement',f"{_s(booking.get('measurement_cbm'),'0')} CBM"),
      ('Packages',f"{_s(booking.get('package_qty'),'0')} {_s(booking.get('package_unit'),'PKGS')}",'Containers',booking.get('container_summary')),
      ('ETD',_fmt(booking.get('etd')),'ETA',_fmt(booking.get('eta'))),
      ('Liner',booking.get('liner') or booking.get('carrier'),'Vessel',booking.get('vessel')),
      ('Mother Vessel',booking.get('m_vessel') or booking.get('mother_vessel'),'Voyage',booking.get('voyage')),
    ],stl,header='Booking Details',color=BLUE),Spacer(1,4*mm)]
    story += [_grid([
      ('POL',booking.get('pol'),'POR',booking.get('por')),
      ('POD',booking.get('pod'),'Final Destination',booking.get('final_destination')),
      ('Transshipment Port',booking.get('transhipment_port') or booking.get('transhipment_port'),'Vessel',booking.get('vessel')),
    ],stl,header='Routing & Vessel',color=BLUE),Spacer(1,4*mm)]
    cargo_type=_s(booking.get('cargo_type'),'').upper(); is_air=cargo_type=='AIR'; is_cy='CY' in _s(booking.get('cy_place'),'').upper()
    schedule=[('CY Date',_fmt(booking.get('cy_date')),'CY Place',booking.get('cy_place')),('Customer Return Date',_fmt(booking.get('customer_return_date')),'Return Place',booking.get('return_place'))]
    if not is_air and not is_cy:
        schedule.insert(1,('CFS Date',_fmt(booking.get('cfs_date')),'CFS Place',booking.get('cfs_place')))
    if not is_air: story += [_grid(schedule,stl,header='Terminal Schedule',color=GOLD),Spacer(1,4*mm)]
    remark=_s(booking.get('remark'),'')
    if remark: story += [Paragraph('<b>Remarks</b>',stl['label']),Paragraph(remark.replace('\n','<br/>'),stl['body']),Spacer(1,4*mm)]
    sig=Table([[Paragraph('Yours sincerely,',stl['body']),Paragraph('_'*30,stl['body'])],[Spacer(1,14*mm),Paragraph(f"<b>{COMPANY['signer_name']}</b><br/>{COMPANY['signer_title']}",stl['body'])]],colWidths=[90*mm,90*mm]); sig.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(0,0),(-1,-1),'CENTER')])); story += [Spacer(1,7*mm),sig]
    doc.build(story,onFirstPage=_footer,onLaterPages=_footer); return output_path

def _footer(canvas,doc):
    canvas.saveState(); canvas.setFont(THAI_FONT,8); canvas.setFillColor(colors.grey); canvas.drawCentredString(A4[0]/2,10*mm,f'Page {doc.page}'); canvas.restoreState()
