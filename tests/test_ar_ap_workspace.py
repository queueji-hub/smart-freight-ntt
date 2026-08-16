from pathlib import Path


def test_ar_ap_workspace_contract():
    source = Path("views/ar_ap_workspace.py").read_text(encoding="utf-8")
    for text in [
        "AR / Outstanding Control",
        "Accounts Receivable Aging",
        "Statement of Account (SOA)",
        "Payment Register",
        "Record Payment",
        "record_payment",
        "outstanding",
        "overdue",
    ]:
        assert text in source


def test_ar_ap_workspace_uses_finance_ssot():
    source = Path("views/ar_ap_workspace.py").read_text(encoding="utf-8")
    assert "from managers.invoice_manager import list_invoices, record_payment" in source
