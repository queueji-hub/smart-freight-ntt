from pathlib import Path


def test_booking_pdf_generates_draft(tmp_path):
    from pdf.booking_pdf import generate_booking_pdf

    output = tmp_path / "booking.pdf"
    booking = {
        "booking_no": "BK-TEST-0001",
        "carrier_booking_no": "CARRIER-001",
        "customer_name": "Erawan",
        "job_type": "SE",
        "shipper": "Shipper",
        "consignee": "Consignee",
        "etd": "2026-08-25",
        "eta": "2026-10-06",
        "pol": "Laem Chabang",
        "por": "Laem Chabang",
        "transhipment_port": "Singapore",
        "pod": "Rotterdam",
        "liner": "Sample Liner",
        "vessel": "TEST VESSEL",
        "m_vessel": "",
        "voyage": "TEST001",
        "final_destination": "Rotterdam",
        "mode": "SEA",
        "cargo_type": "FCL",
        "container_type": "40'HC",
        "container_quantity": 1,
        "container_summary": "40'HC x 1",
        "cy_date": "2026-08-22",
        "cy_place": "Laem Chabang",
        "customer_return_date": "2026-08-21",
        "return_place": "Laem Chabang",
    }

    result = generate_booking_pdf(booking, output_path=str(output), approval_status="Draft")
    assert result == str(output)
    assert output.exists()
    assert output.stat().st_size > 1000


def test_invoice_pdf_generates_draft(tmp_path):
    from pdf.invoice_pdf import generate_invoice_pdf

    output = tmp_path / "invoice.pdf"
    invoice = {
        "doc_type": "INV",
        "doc_no": "INV-TEST-0001",
        "customer_name": "Erawan",
        "issue_date": "2026-08-15",
        "due_date": "2026-09-14",
        "currency": "THB",
        "subtotal": 1000,
        "vat_amount": 70,
        "total_amount": 1070,
        "outstanding": 1070,
        "approval_status": "Draft",
        "status": "Draft",
        "items": [
            {
                "description": "Ocean Freight",
                "quantity": 1,
                "unit_price": 1000,
                "amount": 1000,
                "tax_type": "VAT 7%",
                "wht_type": "None",
            }
        ],
    }

    result = generate_invoice_pdf(invoice, output_path=str(output))
    assert result == str(output)
    assert Path(result).exists()
    assert output.stat().st_size > 1000


def test_profitability_pdf_generates(tmp_path):
    from pdf.profitability_pdf import generate_profitability_pdf

    output = tmp_path / "profitability.pdf"
    job = {
        "job_no": "JOB-2608-0001",
        "customer_name": "Erawan",
        "mode": "Sea",
        "pol": "Laem Chabang",
        "pod": "Rotterdam",
        "etd": "2026-08-25",
        "eta": "2026-10-06",
        "status": "In Transit",
    }
    profit = {
        "ar_estimated": 100000,
        "ar_actual": 95000,
        "ap_estimated": 60000,
        "ap_accrued": 5000,
        "ap_actual": 45000,
        "ap_posted": 0,
        "actual_net_profit": 45000,
    }

    result = generate_profitability_pdf(job, profit, output_path=str(output))
    assert result == str(output)
    assert output.exists()
    assert output.stat().st_size > 1000
