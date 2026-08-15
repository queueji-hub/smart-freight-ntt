from core.booking_presentation import applicable_fields, booking_profile, container_lines, vessel_display


def test_sea_fcl_visibility():
    flags = applicable_fields(booking_profile({"mode": "SEA", "cargo_type": "FCL"}))
    assert flags["container_type"]
    assert flags["cy"]
    assert not flags["cfs"]
    assert flags["container_return"]
    assert not flags["cbm"]


def test_air_visibility():
    flags = applicable_fields(booking_profile({"mode": "AIR", "cargo_type": "AIR"}))
    assert not flags["container_type"]
    assert flags["weight"]
    assert flags["chargeable_weight"]
    assert flags["cfs"]
    assert not flags["cy"]
    assert not flags["vessel"]


def test_vessel_fallback():
    assert vessel_display({"mother_vessel": "", "vessel": "TEST VESSEL"}) == "TEST VESSEL"
    assert vessel_display({"mother_vessel": "MOTHER ONE", "vessel": "FEEDER ONE"}) == "MOTHER ONE"


def test_container_lines_normalize_and_skip_invalid_rows():
    rows = container_lines([
        {"container_type": "40'HC", "quantity": 3},
        {"type": "20'GP", "qty": "2"},
        {"container_type": "", "quantity": 1},
        {"container_type": "40'HC", "quantity": 0},
    ])
    assert rows == [
        {"container_type": "40'HC", "quantity": 3},
        {"container_type": "20'GP", "quantity": 2},
    ]
