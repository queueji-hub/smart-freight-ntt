"""
Application Configuration
Smart Freight NTT,
Production-ready configuration file
"""

from pathlib import Path

# =========================================================
# PATH CONFIGURATION
# =========================================================
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
TEMP_DIR = BASE_DIR / "temp"
LOG_DIR = BASE_DIR / "logs"

DB_PATH = DATA_DIR / "smart_freight.db"

for directory in [DATA_DIR, OUTPUT_DIR, ASSETS_DIR, TEMP_DIR, LOG_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# =========================================================
# APPLICATION INFO
# =========================================================
APP_NAME = "Smart Freight NTT,"
APP_VERSION = "3.0.0"
APP_DESCRIPTION = "Enterprise Freight Forwarding Operating System"
DEFAULT_CURRENCY = "THB"
DEFAULT_LANGUAGE = "EN"
TIMEZONE = "Asia/Bangkok"

# =========================================================
# COMPANY PROFILE
# =========================================================
COMPANY = {
    "name": "NATTAYARAAT CO., LTD.",
    "name_th": "บริษัท ณัฏฐยาราชย์ จำกัด",
    "name_en": "NATTAYARAAT CO., LTD.",
    "short_name": "NATTAYARAAT",
    "tax_id": "073-556-800-4823",
    "address_line1": "59/9 THE BALANZ ZIGMA VILLAGE, MOO4, SOI BANGKRATHUEK 3,",
    "address_line2": "BANGKRATHUEK SUBDISTRICT, SAMPHRAN DISTRICT,",
    "address_line3": "NAKHON PATHOM PROVINCE 73210, THAILAND",
    "address_full": "59/9 THE BALANZ ZIGMA VILLAGE, MOO4, SOI BANGKRATHUEK 3, BANGKRATHUEK SUBDISTRICT, SAMPHRAN DISTRICT, NAKHON PATHOM PROVINCE 73210",
    "tel": "063-428-9691",
    "email": "Management@nattayaraat.com",
    "website": "www.nattayaraat.com",
    "logo_path": str(ASSETS_DIR / "logo.png"),
    "signer_name": "Punnarat M. (Spicy)",
    "signer_title": "Managing Director",
    "bank_name": "",
    "bank_account_name": "",
    "bank_account_no": "",
    "swift_code": "",
}

def get_company_signature():
    """Returns a formatted string of company details for documents/emails."""
    return (f"{COMPANY['name']}\n"
            f"{COMPANY['address_line1']}\n{COMPANY['address_line2']}\n{COMPANY['address_line3']}\n"
            f"Tel: {COMPANY['tel']} | Web: {COMPANY['website']}")

# =========================================================
# BUSINESS RULES & DEFAULTS
# =========================================================
JOB_TYPES = {"SE": "Sea Export", "SI": "Sea Import", "AE": "Air Export", "AI": "Air Import", "TE": "Truck Export", "TI": "Truck Import"}
CARGO_TYPES = ["FCL", "LCL", "AIR", "TRUCK"]
CONTAINER_SIZES = ["1x20'GP", "1x40'GP", "1x40'HC", "1x40'HQ", "1x20'OT", "1x40'OT", "1x20'FR", "1x40'FR", "Other"]
SHIPMENT_STATUS = ["Proceed", "Finished", "Closed", "Canceled"]
BOOKING_STATUS = ["Proceed", "Finished", "Closed", "Canceled"]
PAYMENT_STATUS = ["Unpaid", "Partial", "Paid", "Cancelled"]

VAT_RATE = 0.07
TAX_TYPES = ["VAT 7%", "Non-VAT", "Advance"]
WHT_TYPES = ["None", "1%", "3%"]

DOC_PREFIX = {
    "quotation": "QT", "booking": "BK", "shipment": "JOB",
    "invoice": "INV", "billing_note": "BN", "credit_note": "CN",
    "debit_note": "DN", "statement": "SOA",
}

PDF_SETTINGS = {
    "page_size": "A4", "margin_top": 40, "margin_bottom": 40,
    "margin_left": 40, "margin_right": 40, "font": "Helvetica", "font_size": 9,
}

DASHBOARD_LIMITS = {
    "recent_shipments": 10, "recent_bookings": 10,
    "recent_invoices": 10, "recent_customers": 10,
}

# =========================================================
# SECURITY & EMAIL
# =========================================================
SESSION_EXPIRE_HOURS = 24
PASSWORD_MIN_LENGTH = 6
ENABLE_AUDIT_LOG = True

EMAIL_SETTINGS = {
    "smtp_server": "", "smtp_port": 587,
    "smtp_username": "", "smtp_password": "", "use_tls": True,
}

DEFAULT_TERMS = """Rent / Storage / DEM / DET / Repair and others Import Duty & Tax, if any, are payable by consignee account. 
The above rate is subject to change without prior notice. Loading and unloading are to be arranged by shipper / consignee. 
The above rate excludes Export / Import License fees. Import Duty and Tax payment must be arranged by Importer of Record. 
All invoices are payable within 30 days from invoice date. All quoted charges and rates are exclusive of 7% VAT.
Overnight charge: THB 3,500 / Day, Free time: 3 Hours. Other charges as per actual receipt."""

# =========================================================
# SYSTEM FLAGS
# =========================================================
DEBUG_MODE = False
ENABLE_AUTO_BACKUP = True
ENABLE_PDF_LOGO = True
ENABLE_SESSION_RESTORE = True
ENABLE_CLOUD_SYNC = False