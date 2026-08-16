from pathlib import Path


def test_finance_v2_imports_and_reuses_payment_engine():
    import views.finance_v2_view  # noqa: F401
    source = Path("views/finance_v2_view.py").read_text(encoding="utf-8")
    assert "record_payment" in source
    assert "create_invoice" in source
    assert "from pdf.invoice_pdf import generate_invoice_pdf" in source
    assert source.index("from pdf.invoice_pdf import generate_invoice_pdf") > source.index("def _pdf")


def test_finance_v2_uses_charge_master_for_new_lines():
    source = Path("views/finance_v2_view.py").read_text(encoding="utf-8")
    assert "list_charges" in source
    assert "Charge" in source
