import os
import zipfile
from fpdf import FPDF
from datetime import datetime
from managers.tenant_context import get_current_tenant_id
from managers.document_numbering_service import generate_document_number

class SmartFreightPDF(FPDF):
    def __init__(self, title="Smart Freight NTT"):
        super().__init__()
        self.title_text = title
        self.tenant_id = get_current_tenant_id()
        
        # Thai font support with fallback
        self.has_thai = False
        font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Sarabun-Regular.ttf')
        if os.path.exists(font_path):
            try:
                self.add_font('Sarabun', '', font_path, uni=True)
                self.set_font('Sarabun', '', 10)
                self.has_thai = True
            except Exception:
                self.set_font('Arial', '', 10)
        else:
            self.set_font('Arial', '', 10)
        
    def header(self):
        font_name = 'Sarabun' if self.has_thai else 'Arial'
        self.set_font(font_name, 'B', 15) if not self.has_thai else self.set_font(font_name, '', 15)
        self.cell(0, 10, self.title_text, 0, 1, 'C')
        self.set_font(font_name, 'I', 8) if not self.has_thai else self.set_font(font_name, '', 8)
        self.cell(0, 5, f"Tenant: {self.tenant_id}", 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        font_name = 'Sarabun' if self.has_thai else 'Arial'
        self.set_font(font_name, 'I', 8) if not self.has_thai else self.set_font(font_name, '', 8)
        self.cell(0, 10, f'Page {self.page_no()} - Confidential - Smart Freight NTT', 0, 0, 'C')

def generate_job_sheet_pdf(job_data: dict, profit_data: dict, milestones: list) -> str:
    pdf = SmartFreightPDF(title="JOB SHEET")
    pdf.add_page()
    
    # 1. Job Header
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Job No: {job_data.get('job_no')} | Status: {job_data.get('status')}", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Customer: {job_data.get('customer_name')}", 0, 1)
    pdf.cell(0, 6, f"Salesperson: {job_data.get('sales_person')}", 0, 1)
    pdf.cell(0, 6, f"Routing: {job_data.get('pol')} -> {job_data.get('pod')}", 0, 1)
    pdf.cell(0, 6, f"ETD: {job_data.get('etd')} / ETA: {job_data.get('eta')}", 0, 1)
    pdf.cell(0, 6, f"HBL: {job_data.get('hbl_no')} / MBL: {job_data.get('mbl_no')}", 0, 1)
    
    # 2. Milestones
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "OPERATIONAL MILESTONES", 0, 1)
    pdf.set_font('Arial', '', 9)
    for m in milestones:
        pdf.cell(0, 5, f" - {m.get('milestone_name')}: Planned {m.get('planned_date')} | Actual {m.get('actual_date')}", 0, 1)
        
    # 3. Financials
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "FINANCIAL CONTROL", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, f"Estimated Revenue: {profit_data.get('ar_estimated')} | Actual Revenue: {profit_data.get('ar_actual')}", 0, 1)
    pdf.cell(0, 5, f"Estimated Cost: {profit_data.get('ap_estimated')} | Accrued Cost: {profit_data.get('ap_accrued')} | Actual Cost: {profit_data.get('ap_actual')}", 0, 1)
    pdf.cell(0, 5, f"Gross Profit: {profit_data.get('actual_net_profit')}", 0, 1)
    
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, f"Generated At: {datetime.now()}", 0, 1)
    
    os.makedirs('tmp', exist_ok=True)
    filename = f"tmp/{job_data.get('job_no')}_JobSheet.pdf"
    pdf.output(filename)
    return filename

def generate_company_monthly_pdf(month: str, year: str, data: dict) -> str:
    pdf = SmartFreightPDF(title=f"MONTHLY PERFORMANCE REPORT - {month} {year}")
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, "EXECUTIVE SUMMARY", 0, 1)
    pdf.set_font('Arial', '', 10)
    
    ops = data.get('operations', {})
    pdf.cell(0, 6, f"Total Jobs: {ops.get('total_jobs')} (Export: {ops.get('export_jobs')}, Import: {ops.get('import_jobs')})", 0, 1)
    
    rev = data.get('revenue', {})
    cost = data.get('cost', {})
    prof = data.get('profit', {})
    pdf.cell(0, 6, f"Total Revenue: {rev.get('actual_revenue')} | Total Cost: {cost.get('actual_cost')}", 0, 1)
    pdf.cell(0, 6, f"Gross Profit: {prof.get('actual_gp')} | Margin: {prof.get('gross_margin_pct')}%", 0, 1)
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "SALESPERSON BREAKDOWN", 0, 1)
    pdf.set_font('Arial', '', 9)
    for sp in data.get('sales', []):
        pdf.cell(0, 5, f"{sp.get('sales_person')}: Jobs={sp.get('total_jobs')}, Rev={sp.get('actual_revenue')}, GP={sp.get('actual_gp')}", 0, 1)

    os.makedirs('tmp', exist_ok=True)
    filename = f"tmp/Company_Report_{month}_{year}.pdf"
    pdf.output(filename)
    return filename

def generate_document_pack(job_data: dict, profit_data: dict, milestones: list) -> str:
    job_sheet_path = generate_job_sheet_pdf(job_data, profit_data, milestones)
    pack_path = f"tmp/{job_data.get('job_no')}_DocPack.zip"
    with zipfile.ZipFile(pack_path, 'w') as zipf:
        zipf.write(job_sheet_path, arcname=os.path.basename(job_sheet_path))
    return pack_path

def generate_salesperson_monthly_pdf(month: str, year: str, data: dict, sp_name: str) -> str:
    pdf = SmartFreightPDF(title=f"SALES PERFORMANCE - {sp_name} ({month} {year})")
    pdf.add_page()
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, "EXECUTIVE SUMMARY", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Total Jobs: {len(data)}", 0, 1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "JOB BREAKDOWN", 0, 1)
    pdf.set_font('Arial', '', 9)
    for job in data:
        pdf.cell(0, 5, f"Job: {job.get('job_no')} | Rev: {job.get('ar_actual')} | GP: {job.get('actual_net_profit')}", 0, 1)
    os.makedirs('tmp', exist_ok=True)
    filename = f"tmp/Sales_Report_{sp_name}_{month}_{year}.pdf"
    pdf.output(filename)
    return filename
