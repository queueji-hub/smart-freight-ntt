from core.freight_rules import get_freight_profile, resolve_vessel


def test_sea_fcl_profile():
    p = get_freight_profile("SEA", "FCL")
    assert (p.volume_kind, p.receiving_kind) == ("CONTAINER", "CY")
    assert p.show_container_type
    assert p.show_cy
    assert not p.show_cfs
    assert p.show_container_return
    assert p.show_vessel


def test_sea_lcl_profile():
    p = get_freight_profile("SEA", "LCL")
    assert (p.volume_kind, p.receiving_kind) == ("CBM", "CFS")
    assert p.show_cbm
    assert p.show_cfs
    assert not p.show_cy
    assert not p.show_container_return
    assert p.show_vessel


def test_air_profile():
    p = get_freight_profile("AIR", "AIR")
    assert (p.volume_kind, p.receiving_kind) == ("KG", "CFS")
    assert p.show_weight
    assert p.show_chargeable_weight
    assert p.show_cfs
    assert not p.show_cy
    assert not p.show_vessel


def test_truck_profiles():
    ftl = get_freight_profile("TRUCK", "FTL")
    ltl = get_freight_profile("TRUCK", "LTL")
    assert (ftl.volume_kind, ftl.receiving_kind) == ("TRUCK", "CFS")
    assert (ltl.volume_kind, ltl.receiving_kind) == ("CBM", "CFS")
    assert ltl.show_cbm
    assert not ftl.show_cbm


def test_vessel_fallback():
    assert resolve_vessel("", "EVER STAR") == "EVER STAR"
    assert resolve_vessel("MAERSK MANCHESTER", "EVER STAR") == "MAERSK MANCHESTER"
