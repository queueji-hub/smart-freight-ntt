"""Shared document action vocabulary and status labels."""

DOCUMENT_ACTIONS = ("PDF", "Edit", "Approve")

DOCUMENT_STATUSES = (
    "Draft",
    "Pending Approval",
    "Approved",
    "Issued",
    "Cancelled",
)

JOB_STATUSES = (
    "Planned",
    "In Progress",
    "Completed",
    "Closed",
    "Cancelled",
)


def action_label(action: str) -> str:
    """Return the canonical short label used across document lists."""
    normalized = str(action or "").strip().lower()
    mapping = {
        "pdf": "PDF",
        "edit": "Edit",
        "approve": "Approve",
        "duplicate": "Duplicate",
        "delete": "Delete",
        "cancel": "Cancel",
        "save": "Save",
        "submit": "Submit",
        "close": "Close",
    }
    return mapping.get(normalized, str(action or "").strip().title())


def status_label(status: str) -> str:
    """Normalize common legacy status spellings for display only."""
    raw = str(status or "").strip().replace("_", " ")
    key = raw.lower()
    mapping = {
        "draft": "Draft",
        "pending": "Pending Approval",
        "pending approval": "Pending Approval",
        "approved": "Approved",
        "issued": "Issued",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    return mapping.get(key, raw.title())
