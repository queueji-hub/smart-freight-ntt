from __future__ import annotations
"""
Structured Finance Document Workspace (Progress Transport Systems Standard).
Provides Single Source of Truth UI for Billing Note, Receipt / Tax Invoice,
Credit Note, Debit Note and Statement of Account (SOA).
"""

from typing import List, Dict, Any
import streamlit as st
import pandas as pd
from managers.invoice_manager import get_outstanding_summary, list_invoices
from views import finance_v2_view


def _summary(rows: List[Dict[str, Any]]) -> None:
    billed = sum(float(r.get("total_amount") or r.get("grand_total") or 0) for r in rows if str(r.get("status", "")).upper() != "CANCELLED")
    outstanding = sum(float(r.get("outstanding") or 0) for r in rows if str(r.get("status", "")).upper() != "CANCELLED")
    paid = sum(float(r.get("paid_amount") or 0) for r in rows) if any(r.get("paid_amount") for r in rows) else max(billed - outstanding, 0.0)
    a, b, c = st.columns(3)
    a.metric("Total Billed", f"{billed:,.2f}")
    a.metric("Total Paid", f"{paid:,.2f}")
    a.metric("Outstanding", f"{outstanding:,.2f}")


def render():
    finance_v2_view.render()
