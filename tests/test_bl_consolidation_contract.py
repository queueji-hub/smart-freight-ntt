from managers.bl_consolidation_service import _norm_place, build_bl_document_payload
from managers.bl_workflow_service import BL_TYPES


def test_place_normalization_is_stable():
    assert _norm_place("Laem Chabang, Thailand") == "LAE"
    assert _norm_place("Naha, Okinawa, Japan") == "NAH"


def test_new_workflow_has_single_bl_concept():
    assert BL_TYPES == ("BL",)


def test_document_payload_carries_consolidation_context():
    payload = build_bl_document_payload(
        {"bl_no": "NATTA-LCHNAH2608003", "consol_seq": 3, "shipper": "A"},
        job={"job_no": "JOB-2608-0014", "vessel": "TEST VESSEL"},
        containers=[{"container_no": "CAIU8226953"}],
    )
    assert payload["bl"]["consol_seq"] == 3
    assert payload["job"]["job_no"] == "JOB-2608-0014"
    assert payload["containers"][0]["container_no"] == "CAIU8226953"


def test_manager_keeps_multi_bl_contract():
    source = open("managers/bl_workflow_service.py", encoding="utf-8").read()
    assert '"consol_no"' in source
    assert '"consol_seq"' in source
    assert 'list_job_bls' in source
