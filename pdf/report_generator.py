import os
import zipfile
from datetime import datetime
from managers.tenant_context import get_current_tenant_id


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_REGULAR = os.path.join(BASE_DIR, "assets", "fonts", "Sarabun-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "assets", "fonts", "Sarabun-Bold.ttf")
TMP_DIR = os.path.join(BASE_DIR, "tmp")


def _build_pdf(title="Smart Freight NTT", approval_status="Approved"):
    """Create the PDF object lazily so importing the view never imports fpdf."""
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError(
            "PDF generation is unavailable because fpdf2 is not installed. "
            "Add fpdf2 to requirements.txt and redeploy."
        ) from exc

    class SmartFreightPDF(FPDF):
        def __init__(self):
            super().__init__()
            self.title_text = title
            self.tenant_id = get_current_tenant_id()
            self.has_thai = False
            self.font_regular = FONT_REGULAR
            self.font_bold = FONT_BOLD

            if os.path.exists(self.font_regular):
                try:
                    self.add_font("Sarabun", "", self.font_regular)
                    if os.path.exists(self.font_bold):
                        self.add_font("Sarabun", "B", self.font_bold)
                    self.set_font("Sarabun", "", 10)
                    self.has_thai = True
                except Exception:
                    self.set_font("Helvetica", "", 10)
            else:
                self.set_font("Helvetica", "", 10)

        def _font(self, style="", size=10):
            name = "Sarabun" if self.has_thai else "Helvetica"
            self.set_font(name, style, size)

        def header(self):
            self._font("", 15)
            self.cell(0, 10, self.title_text, 0, 1, "C")
            self._font("", 8)
            self.cell(0, 5, f"Tenant: {self.tenant_id}", 0, 1, "C")
            self.ln(5)

            if str(approval_status).strip().lower() in {"draft", "pending approval", "pending"}:
                self._font("B", 30)
                self.set_text_color(220, 220, 220)
                self.cell(0, 18, "DRAFT", 0, 1, "C")
                self.set_text_color(0, 0, 0)
                self.ln(2)

        def footer(self):
            self.set_y(-15)
            self._font("", 8)
            self.cell(0, 10, f"Page {self.page_no()} - Confidential - Smart Freight NTT", 0, 0, "C")

    return SmartFreightPDF()


def _ensure_tmp():
    os.makedirs(TMP_DIR, exist_ok=True)


def generate_job_sheet_pdf(job_data: dict, profit_data: dict, milestones: list, approval_status="Approved") -> str:
    pdf = _build_pdf(title="JOB SHEET", approval_status=approval_status)
    pdf.add_page()

    pdf._font("B", 12)
    pdf.cell(0, 10, f"Job No: {job_data.get('job_no')} | Status: {job_data.get('status')}", 0, 1)

    pdf._font("", 10)
    pdf.cell(0, 6, f"Customer: {job_data.get('customer_name') or job_data.get('customer_id')}", 0, 1)
    pdf.cell(0, 6, f"Sales: {job_data.get('sales_person')}", 0, 1)
    pdf.cell(0, 6, f"Routing: {job_data.get('pol')} -> {job_data.get('pod')}", 0, 1)
    pdf.cell(0, 6, f"ETD: {job_data.get('etd')} / ETA: {job_data.get('eta')}", 0, 1)
    pdf.cell(0, 6, f"HBL: {job_data.get('hbl_no')} / MBL: {job_data.get('mbl_no')}", 0, 1)

    pdf.ln(5)
    pdf._font("B", 11)
    pdf.cell(0, 8, "OPERATIONAL MILESTONES", 0, 1)
    pdf._font("", 9)
    for milestone in milestones or []:
        pdf.cell(
            0,
            5,
            f" - {milestone.get('milestone_name')}: Planned {milestone.get('planned_date')} | Actual {milestone.get('actual_date')}",
            0,
            1,
        )

    pdf.ln(5)
    pdf._font("B", 11)
    pdf.cell(0, 8, "FINANCIAL CONTROL", 0, 1)
    pdf._font("", 9)
    pdf.cell(0, 5, f"Estimated Revenue: {profit_data.get('ar_estimated')} | Actual Revenue: {profit_data.get('ar_actual')}", 0, 1)
    pdf.cell(0, 5, f"Estimated Cost: {profit_data.get('ap_estimated')} | Accrued Cost: {profit_data.get('ap_accrued')} | Actual Cost: {profit_data.get('ap_actual')}", 0, 1)
    pdf.cell(0, 5, f"Gross Profit: {profit_data.get('actual_net_profit')}", 0, 1)

    pdf.ln(10)
    pdf._font("", 8)
    pdf.cell(0, 5, f"Generated At: {datetime.now()}", 0, 1)

    _ensure_tmp()
    filename = os.path.join(TMP_DIR, f"{job_data.get('job_no')}_JobSheet.pdf")
    pdf.output(filename)
    return filename


def generate_company_monthly_pdf(month: str, year: str, data: dict, approval_status="Approved") -> str:
    pdf = _build_pdf(title=f"MONTHLY PERFORMANCE REPORT - {month} {year}", approval_status=approval_status)
    pdf.add_page()

    pdf._font("B", 11)
    pdf.cell(0, 10, "EXECUTIVE SUMMARY", 0, 1)
    pdf._font("", 10)

    ops = data.get("operations", {})
    pdf.cell(0, 6, f"Total Jobs: {ops.get('total_jobs')} (Export: {ops.get('export_jobs')}, Import: {ops.get('import_jobs')})", 0, 1)

    rev = data.get("revenue", {})
    cost = data.get("cost", {})
    prof = data.get("profit", {})
    pdf.cell(0, 6, f"Total Revenue: {rev.get('actual_revenue')} | Total Cost: {cost.get('actual_cost')}", 0, 1)
    pdf.cell(0, 6, f"Gross Profit: {prof.get('actual_gp')} | Margin: {prof.get('gross_margin_pct')}%", 0, 1)

    pdf.ln(5)
    pdf._font("B", 11)
    pdf.cell(0, 8, "SALESPERSON BREAKDOWN", 0, 1)
    pdf._font("", 9)
    for sp in data.get("sales", []):
        pdf.cell(0, 5, f"{sp.get('sales_person')}: Jobs={sp.get('total_jobs')}, Rev={sp.get('actual_revenue')}, GP={sp.get('actual_gp')}", 0, 1)

    _ensure_tmp()
    filename = os.path.join(TMP_DIR, f"Company_Report_{month}_{year}.pdf")
    pdf.output(filename)
    return filename


def generate_document_pack(job_data: dict, profit_data: dict, milestones: list, approval_status="Approved") -> str:
    job_sheet_path = generate_job_sheet_pdf(job_data, profit_data, milestones, approval_status=approval_status)
    _ensure_tmp()
    pack_path = os.path.join(TMP_DIR, f"{job_data.get('job_no')}_DocPack.zip")
    with zipfile.ZipFile(pack_path, "w") as zipf:
        zipf.write(job_sheet_path, arcname=os.path.basename(job_sheet_path))
    return pack_path


def generate_salesperson_monthly_pdf(month: str, year: str, data: list, sp_name: str, approval_status="Approved") -> str:
    pdf = _build_pdf(title=f"SALES PERFORMANCE - {sp_name} ({month} {year})", approval_status=approval_status)
    pdf.add_page()
    pdf._font("B", 11)
    pdf.cell(0, 10, "EXECUTIVE SUMMARY", 0, 1)
    pdf._font("", 10)
    pdf.cell(0, 6, f"Total Jobs: {len(data or [])}", 0, 1)
    pdf.ln(5)
    pdf._font("B", 11)
    pdf.cell(0, 8, "JOB BREAKDOWN", 0, 1)
    pdf._font("", 9)
    for job in data or []:
        pdf.cell(0, 5, f"Job: {job.get('job_no')} | Revenue: {job.get('ar_actual')} | GP: {job.get('actual_net_profit')}", 0, 1)
    _ensure_tmp()
    filename = os.path.join(TMP_DIR, f"Sales_Report_{sp_name}_{month}_{year}.pdf")
    pdf.output(filename)
    return filename
