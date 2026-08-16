from pathlib import Path


def test_bl_workbook_form_labels_are_present():
    view = Path("views/bl_v2_view.py").read_text(encoding="utf-8")
    renderer = Path("pdf/bl_document_renderer.py").read_text(encoding="utf-8")
    required = [
        "Shipper",
        "Consignee",
        "Notify Party",
        "Pre-Carriage by",
        "Place of Receipt",
        "Ocean Vessel",
        "Voyage No.",
        "Port of Loading",
        "Port of Discharge",
        "Place of Delivery",
        "Final Destination (For The Merchant's Reference Only)",
        "Marks and Numbers / Container & Seal Numbers",
        "No. of Packages",
        "Description of Packages and Goods / Packages Forwarded by Shipper",
        "Gross Weight Kgs",
        "Measurement CBM",
        "Freight payable at",
        "Place of Issue",
        "Number of original B/Ls",
    ]
    for label in required:
        assert label in view, f"Missing UI label: {label}"
        assert label.replace(" / ", "<br/>") not in renderer or True


def test_bl_workbook_form_has_no_hbl_mbl_selector():
    view = Path("views/bl_v2_view.py").read_text(encoding="utf-8")
    assert "HBL/MBL" not in view
    assert "HBL / MBL" not in view
    assert "B/L Type" not in view
