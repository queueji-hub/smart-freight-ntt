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


def test_credit_and_debit_note_pdf_generates(tmp_path):
    from pdf.invoice_pdf import generate_invoice_pdf

    for doc_type in ["CN", "DN"]:
        output = tmp_path / f"{doc_type.lower()}.pdf"
        doc = {
            "doc_type": doc_type,
            "doc_no": f"{doc_type}-TEST-0001",
            "customer_name": "Erawan",
            "issue_date": "2026-08-15",
            "currency": "THB",
            "subtotal": 500,
            "vat_amount": 35,
            "total_amount": 535,
            "reason": "Price correction per agreement",
            "items": [
                {
                    "description": "Freight Adjustment",
                    "quantity": 1,
                    "unit_price": 500,
                    "amount": 500,
                    "tax_type": "VAT 7%",
                    "wht_type": "None",
                }
            ],
        }
        res = generate_invoice_pdf(doc, output_path=str(output))
        assert res == str(output)
        assert output.exists()
        assert output.stat().st_size > 1000


def test_quotation_pdf_generates(tmp_path):
    from pdf.quotation_pdf import generate_quotation_pdf

    output = tmp_path / "quote.pdf"
    quote_data = {
        "quote_no": "QT-TEST-0001",
        "customer_name": "Erawan Trading Co., Ltd.",
        "quote_date": "2026-08-15",
        "valid_until": "2026-09-15",
        "pol": "Bangkok Port",
        "pod": "Singapore",
        "job_type": "SE",
        "mode": "SEA",
        "cargo_type": "FCL",
        "items": [
            {
                "description": "Ocean Freight",
                "quantity": 1,
                "unit_price": 800,
                "amount": 800,
                "currency": "USD",
            }
        ],
    }
    res = generate_quotation_pdf(quote_data, quote_data["items"], output_path=str(output))
    assert res == str(output)
    assert output.exists()
    assert output.stat().st_size > 1000


def test_receipt_pdf_generates(tmp_path):
    from pdf.receipt_pdf import generate_receipt_pdf

    output = tmp_path / "receipt.pdf"
    inv_data = {
        "doc_no": "REC-TEST-0001",
        "doc_type": "REC",
        "customer_name": "Erawan Trading Co., Ltd.",
        "issue_date": "2026-08-15",
        "total_amount": 10700.0,
        "items": [
            {
                "description": "Ocean Freight",
                "quantity": 1,
                "unit_price": 10000.0,
                "amount": 10000.0,
                "tax_type": "VAT 7%",
            }
        ],
    }
    res = generate_receipt_pdf(inv_data, output_path=str(output))
    assert res == str(output)
    assert output.exists()
    assert output.stat().st_size > 1000


def test_company_bl_pdf_generates(tmp_path):
    from pdf.bl_document_renderer import generate_company_bl_pdf

    output = tmp_path / "bl.pdf"
    payload = {
        "bl": {
            "bl_no": "NATTA-BKKSI2608001",
            "bl_type": "BL",
            "shipper": "Thai Exporter Co.",
            "consignee": "SG Importer Pte.",
            "port_of_loading": "Bangkok",
            "port_of_discharge": "Singapore",
            "vessel_name": "WAN HAI 301",
            "voyage_no": "N120",
        },
        "containers": [
            {
                "container_no": "WHLU1234567",
                "container_size": "20'GP",
                "seal_no": "SL9988",
                "gross_weight": 12000,
                "packages": "500 Cartons",
                "goods_description": "Consumer Goods",
            }
        ],
        "charges": [
            {
                "charge_name": "Ocean Freight",
                "prepaid": "800.00 USD",
                "collect": "",
            }
        ],
    }
    res = generate_company_bl_pdf(payload, output_path=str(output))
    assert res == str(output)
    assert output.exists()
    assert output.stat().st_size > 1000

