"""Quotation write service that keeps master IDs canonical with legacy compatibility."""
from __future__ import annotations

from typing import Any, Dict, List

from managers.quotation_manager import create_quotation as _legacy_create_quotation
from managers.quotation_manager import update_quotation as _legacy_update_quotation
from managers.ssot_write_adapter import sync_quotation_master_ids


def create_quotation_ssot(data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    customer_id = data.get("customer_id")
    sales_id = data.get("sales_id")
    if customer_id is None:
        raise ValueError("customer_id is required for new quotations.")
    quotation_no = _legacy_create_quotation(data, items)
    sync_quotation_master_ids(quotation_no, customer_id=customer_id, sales_id=sales_id)
    return quotation_no


def update_quotation_ssot(quotation_no: str, data: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
    customer_id = data.get("customer_id")
    sales_id = data.get("sales_id")
    if customer_id is None:
        raise ValueError("customer_id is required for quotation updates.")
    _legacy_update_quotation(quotation_no, data, items)
    sync_quotation_master_ids(quotation_no, customer_id=customer_id, sales_id=sales_id)
