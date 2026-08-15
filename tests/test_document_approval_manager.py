import pytest

import managers.document_approval_manager as approval


def test_can_approve_is_explicit_by_entity():
    assert approval.can_approve("quotation", {"role": "admin"})
    assert not approval.can_approve("quotation", {"role": "accounting"})
    assert approval.can_approve("invoice", {"role": "accounting"})
    assert approval.can_approve("booking", {"role": "operation"})
    assert not approval.can_approve("booking", {"role": "sales"})


def test_transition_submit_and_approve(monkeypatch):
    state = {"value": "Draft"}
    monkeypatch.setattr(approval, "get_approval_status", lambda entity, doc_no: state["value"])
    monkeypatch.setattr(approval, "set_approval_status", lambda entity, doc_no, status: state.__setitem__("value", status))
    monkeypatch.setattr(approval, "_assert_preflight", lambda entity, doc_no: None)

    assert approval.submit_for_approval("quotation", "QT-1", {"role": "sales"}) == "Pending Approval"
    with pytest.raises(PermissionError):
        approval.approve_document("quotation", "QT-1", {"role": "sales"})
    assert approval.approve_document("quotation", "QT-1", {"role": "admin"}) == "Approved"


def test_invalid_transition_is_rejected(monkeypatch):
    monkeypatch.setattr(approval, "get_approval_status", lambda entity, doc_no: "Approved")
    with pytest.raises(ValueError):
        approval.transition_document("invoice", "INV-1", "Pending Approval", {"role": "accounting"})
