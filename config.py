"""
Application Configuration
Smart Freight NTT
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

# =========================================================
# AUTO CREATE DIRECTORIES
# =========================================================

for directory in [
    DATA_DIR,
    OUTPUT_DIR,
    ASSETS_DIR,
    TEMP_DIR,
    LOG_DIR,
]:
    directory.mkdir(
        exist_ok=True,
        parents=True,
    )

# =========================================================
# APPLICATION INFO
# =========================================================

APP_NAME = "Smart Freight NTT"

APP_VERSION = "3.0.0"

APP_DESCRIPTION = (
    "Enterprise Freight Forwarding "
    "Operating System"
)

DEFAULT_CURRENCY = "THB"

DEFAULT_LANGUAGE = "EN"

TIMEZONE = "Asia/Bangkok"

# =========================================================
# COMPANY PROFILE
# =========================================================

COMPANY = {

    # BASIC
    "name":
        "NATTAYARAAT CO., LTD.",

    "short_name":
        "NATTAYARAAT",

    "tax_id":
        "0735568004823",

    # ADDRESS
    "address_space":
        "",

    "address_line1":
        "59/9 The Balanz Zigma Village, Moo 4, Soi Bangkrathuek 3",

    "address_line2":
        "Bangkrathuek Subdistrict, Sam Phran District",

    "address_line3":
        "Nakhon Pathom 73210, Thailand",

    # CONTACT
    "tel":
        "063-428-9691",

    "email":
        "Management@nattayaraat.com",

    "website":
        "www.nattayaraat.com",

    # BRANDING
    "logo_path":
        str(
            ASSETS_DIR / "logo.png"
        ),

    # SIGNATORY
    "signer_name":
        "Punnarat M. (Spicy)",

    "signer_title":
        "Managing Director",

    # BANK
    "bank_name":
        "",

    "bank_account_name":
        "",

    "bank_account_no":
        "",

    "swift_code":
        "",
}

# =========================================================
# JOB TYPES
# =========================================================

JOB_TYPES = {

    # SEA
    "SE": "Sea Export",
    "SI": "Sea Import",

    # AIR
    "AE": "Air Export",
    "AI": "Air Import",

    # TRUCK
    "TE": "Truck Export",
    "TI": "Truck Import",
}

# =========================================================
# CARGO TYPES
# =========================================================

CARGO_TYPES = [
    "FCL",
    "LCL",
    "AIR",
    "TRUCK",
]

# =========================================================
# CONTAINER TYPES
# =========================================================

CONTAINER_SIZES = [
    "1x20'GP",
    "1x40'GP",
    "1x40'HC",
    "1x40'HQ",
    "1x20'OT",
    "1x40'OT",
    "1x20'FR",
    "1x40'FR",
    "Other",
]

# =========================================================
# SHIPMENT STATUS
# =========================================================

SHIPMENT_STATUS = [
    "Proceed",
    "Finished",
    "Closed",
    "Canceled",
]

# =========================================================
# BOOKING STATUS
# =========================================================

BOOKING_STATUS = [
    "Proceed",
    "Finished",
    "Closed",
    "Canceled",
]

# =========================================================
# BILLING STATUS
# =========================================================

PAYMENT_STATUS = [
    "Unpaid",
    "Partial",
    "Paid",
    "Cancelled",
]

# =========================================================
# TAX SETTINGS
# =========================================================

VAT_RATE = 0.07

TAX_TYPES = [
    "VAT 7%",
    "Non-VAT",
    "Advance",
]

WHT_TYPES = [
    "None",
    "1%",
    "3%",
]

# =========================================================
# DOCUMENT PREFIX
# =========================================================

DOC_PREFIX = {

    "quotation":
        "QT",

    "booking":
        "BK",

    "shipment":
        "JOB",

    "invoice":
        "INV",

    "billing_note":
        "BN",

    "credit_note":
        "CN",

    "debit_note":
        "DN",

    "statement":
        "SOA",
}

# =========================================================
# PDF SETTINGS
# =========================================================

PDF_SETTINGS = {

    "page_size":
        "A4",

    "margin_top":
        40,

    "margin_bottom":
        40,

    "margin_left":
        40,

    "margin_right":
        40,

    "font":
        "Helvetica",

    "font_size":
        9,
}

# =========================================================
# DASHBOARD SETTINGS
# =========================================================

DASHBOARD_LIMITS = {

    "recent_shipments":
        10,

    "recent_bookings":
        10,

    "recent_invoices":
        10,

    "recent_customers":
        10,
}

# =========================================================
# SECURITY SETTINGS
# =========================================================

SESSION_EXPIRE_HOURS = 24

PASSWORD_MIN_LENGTH = 6

ENABLE_AUDIT_LOG = True

# =========================================================
# DEFAULT TERMS & CONDITIONS
# =========================================================

DEFAULT_TERMS = """
Rent / Storage / DEM / DET / Repair and others Import Duty & Tax,
if any, are payable by consignee account.

The above rate is subject to change without prior notice.

Loading and unloading are to be arranged by shipper / consignee.

The above rate excludes Export / Import License fees.

Import Duty and Tax payment must be arranged by
Importer of Record.

All invoices are payable within 30 days from invoice date.

All quoted charges and rates are exclusive of 7% VAT.

Overnight charge:
THB 3,500 / Day
Free time: 3 Hours

Other charges as per actual receipt.

Containers discharged at PAT Port may incur additional charges,
including CIC, PCS, DEM / DET, and Storage.

Free time at consignee site is limited to 3 hours
after gate-in arrival.
""".strip()

# =========================================================
# EMAIL SETTINGS
# =========================================================

EMAIL_SETTINGS = {

    "smtp_server":
        "",

    "smtp_port":
        587,

    "smtp_username":
        "",

    "smtp_password":
        "",

    "use_tls":
        True,
}

# =========================================================
# EXPORT SETTINGS
# =========================================================

EXPORT_SETTINGS = {

    "csv_encoding":
        "utf-8-sig",

    "excel_engine":
        "openpyxl",
}

# =========================================================
# SYSTEM FLAGS
# =========================================================

DEBUG_MODE = False

ENABLE_AUTO_BACKUP = True

ENABLE_PDF_LOGO = True

ENABLE_SESSION_RESTORE = True

ENABLE_CLOUD_SYNC = False