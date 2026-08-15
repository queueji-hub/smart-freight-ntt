from managers.bl_workflow_service import BL_TYPES, _generate_company_bl_no, _port_code


def test_company_bl_number_matches_sample_shape():
    assert _generate_company_bl_no("Laem Chabang, Thailand", "Naha, Okinawa, Japan", "2026-08-25").startswith("NATTA-LCHNAH2608")
    assert len(_generate_company_bl_no("Laem Chabang, Thailand", "Naha, Okinawa, Japan", "2026-08-25")) == 20


def test_port_code_resolution():
    assert _port_code("Laem Chabang, Thailand") == "LCH"
    assert _port_code("Naha, Okinawa, Japan") == "NAH"


def test_new_workflow_has_single_bl_concept():
    assert BL_TYPES == ("BL",)


def test_multi_bl_fields_are_documented_by_model_contract():
    source = open("managers/bl_workflow_service.py", encoding="utf-8").read()
    assert '"consol_no"' in source
    assert '"consol_seq"' in source
    assert 'list_job_bls' in source
