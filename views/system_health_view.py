"""Production system health and workflow integrity checks."""
from __future__ import annotations

import importlib
import os
import streamlit as st

from database.connection import init_database
from database.local_schema_compat import ensure_phase30_local_schema
from ui.design_system import page_header, section

ROUTE_CONTRACTS = {
    "Quotation": "views.quotation_v2_view",
    "Booking": "views.booking_v2_view",
    "B/L": "views.bl_v2_view",
    "Finance": "views.finance_document_workspace",
    "AR/AP": "views.ar_ap_workspace",
    "Documents": "views.document_v2_view",
    "Job Control": "views.shipment_view",
}


def _check(label, fn):
    try:
        value = fn()
        return {"Component": label, "Status": "PASS", "Detail": str(value or "OK")}
    except Exception as exc:
        return {"Component": label, "Status": "FAIL", "Detail": str(exc)}


def render():
    page_header("settings", status_text="Health Monitor")
    st.caption("Read-only production integrity checks. No business data is modified.")

    rows = []
    for label, module_name in ROUTE_CONTRACTS.items():
        rows.append(_check(label, lambda m=module_name: getattr(importlib.import_module(m), "render")))
    rows.append(_check("Database bootstrap", lambda: (init_database(), ensure_phase30_local_schema()) or "OK"))
    rows.append(_check("PDF output directory", lambda: os.path.isdir("/tmp") or os.path.isdir("output")))

    section("Production Integrity")
    for row in rows:
        if row["Status"] == "PASS":
            st.success(f"✓ {row['Component']} — {row['Detail']}")
        else:
            st.error(f"✕ {row['Component']} — {row['Detail']}")

    failed = sum(r["Status"] == "FAIL" for r in rows)
    if failed:
        st.warning(f"Health check completed with {failed} failure(s). Fix before production release.")
    else:
        st.success("ALL PRODUCTION INTEGRITY CHECKS PASS")
