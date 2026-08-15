from unittest.mock import patch

import pytest

from managers.booking_ssot_service import _validate_freight_payload


def test_sea_fcl_requires_customer_and_container():
    with pytest.raises(ValueError, match="customer_id"):
        _validate_freight_payload({"cargo_type": "FCL", "container_summary": "20'GP x 1"})


def test_sea_fcl_clears_cfs_fields():
    payload = {
        "customer_id": 1,
        "cargo_type": "FCL",
        "container_summary": "20'GP x 1",
        "cfs_date": "2026-08-15",
        "cfs_place": "legacy",
    }
    _validate_freight_payload(payload)
    assert payload["cfs_date"] is None
    assert payload["cfs_place"] is None


def test_sea_lcl_requires_cbm_and_clears_cy_fields():
    payload = {
        "customer_id": 1,
        "cargo_type": "LCL",
        "measurement_cbm": 3.2,
        "cy_date": "2026-08-15",
        "cy_place": "legacy",
        "customer_return_date": "2026-08-15",
        "return_place": "legacy",
    }
    _validate_freight_payload(payload)
    assert payload["cy_date"] is None
    assert payload["cy_place"] is None
    assert payload["customer_return_date"] is None
    assert payload["return_place"] is None


def test_air_requires_chargeable_weight():
    with pytest.raises(ValueError, match="chargeable_weight"):
        _validate_freight_payload({"customer_id": 1, "cargo_type": "AIR"})
