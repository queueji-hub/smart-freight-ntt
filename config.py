"""Application configuration."""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"

DB_PATH = DATA_DIR / "smart_freight.db"

# Company information (shown on quotation header)
COMPANY = {
    "name": "NATTAYARAAT CO., LTD.",
    "address_space": "",                                        # ปล่อยว่างไว้เพื่อดันบรรทัด
    "address_line1": "59/9 The Balanz Zigma Village, Moo 4, Soi Bangkrathuek 3",
    "address_line2": "Bangkrathuek Subdistrict, Sam Phran District Nakhon Pathom",
    "address_line3": "Province 73210",
    "tax_id": "0735568004823",
    "tel": "063-428-9691",
    "email": "Management@nattayaraat.com",
    "logo_path": str(ASSETS_DIR / "logo.png"),
    "signer_name": "Punnarat M. (Spicy)",
    "signer_title": "Managing Director",
}

# Job type codes
JOB_TYPES = {
    "SE": "Sea Export",
    "SI": "Sea Import",
    "AE": "Air Export",
    "AI": "Air Import",
    "TE": "Truck Export",
    "TI": "Truck Import",
}

# Default Terms & Conditions
DEFAULT_TERMS = """Rent/Storage/DEM/DET/Repair and others Import Duty & Tax, if any (paid by consignee account)
The above rate subject to change without prior notice.
Loading and unloading are to be arranged by shipper / consignee.
The above rate not include Export / Import Lisence
Import Duty and Tax payment to be arranged by Importer of record
The amount due are and pay able by customer within 30 days after the invoice date
All quoted charges and rates are exclusive 7% VAT
Over Night THB 3,500/Day Free time 3 Hrs
Other charges as per receipt.
Containers discharge at PAT port may incur additional costs, including CIC, PCS, DEM/DET, and Storage charges.
Free time at consignee site only 3 hours after arriving time at gate"""

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
