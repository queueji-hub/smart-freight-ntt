from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bl_renderer_matches_reference_sections():
    source = _text("pdf/bl_document_renderer.py")
    for marker in (
        "BILL OF LADING",
        "B/L No.",
        "Shipper",
        "Consignee",
        "Notify Party",
        "Ocean Vessel / Voyage No.",
        "Port of Loading",
        "Port of Discharge",
        "Place of Delivery",
        "Container & Seal Numbers",
        "No. of Packages",
        "Gross Weight Kgs",
        "Measurement CBM",
        "Freight and Disbursements",
        "Freight payable at",
        "Number of original B/Ls",
        "Signed on behalf of the Carrier",
    ):
        assert marker in source
    assert "HBL" not in source
    assert "MBL" not in source


def test_finance_ui_uses_charge_master_code_and_customer_master():
    source = _text("views/finance_v2_view.py")
    assert "def _charge_master" in source
    assert "charge_code" in source
    assert "Tax ID" in source
    assert "Billing Address" in source
    assert "Reference / Job Ref." in source
    assert "generate_invoice_pdf(payload, customer=customer)" in source


def test_finance_pdf_contains_reference_document_sections():
    source = _text("pdf/invoice_pdf.py")
    for marker in (
        "BILL TO / CUSTOMER",
        "DOCUMENT DETAILS",
        "SHIPPING / DELIVERY ADDRESS",
        "AMOUNT IN WORDS",
        "GRAND TOTAL",
        "Authorized Signature",
    ):
        assert marker in source
