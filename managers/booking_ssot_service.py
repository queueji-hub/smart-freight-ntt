"""Canonical Booking write service.

Keeps new booking records aligned with Master Data IDs and the canonical
freight handling rules while preserving the legacy booking manager API.
"""
from __future__ import annotations

from typing import Any, Dict

from core.freight_rules import get_freight_profile
from managers.booking_manager import create_booking as _legacy_create_booking
from managers.booking_manager import update_booking as _legacy_update_booking
from managers.ssot_write_adapter import sync_booking_master_ids


def _mode_from_payload(data: Dict[str, Any]) -> str:
    cargo = str(data.get("cargo_type") or data.get("cargo") or "").strip().upper()
    if cargo == "AIR":
        return "AIR"
    if cargo == "TRUCK":
        return "TRUCK"
    return "SEA"


def _validate_freight_payload(data: Dict[str, Any]) -> None:
    cargo = str(data.get("cargo_type") or "").strip().upper() or "LCL"
    profile = get_freight_profile(_mode_from_payload(data), cargo)

    if not data.get("customer_id"):
        raise ValueError("customer_id is required for new bookings.")

    if profile.show_container_type and not str(data.get("container_summary") or "").strip():
        raise ValueError("container_summary is required for Sea FCL bookings.")
    if profile.show_cbm and float(data.get("measurement_cbm") or 0) <= 0:
        raise ValueError("measurement_cbm is required for this booking type.")
    if profile.show_chargeable_weight and float(data.get("chargeable_weight") or 0) <= 0:
        raise ValueError("chargeable_weight is required for Air bookings.")

    # Keep mutually exclusive operational fields clean.
    if profile.show_cy:
        data["cfs_date"] = None
        data["cfs_place"] = None
    elif profile.show_cfs:
        data["cy_date"] = None
        data["cy_place"] = None
        data["customer_return_date"] = None
        data["return_place"] = None


def create_booking_ssot(data: Dict[str, Any], user: Dict[str, Any] | None = None) -> str:
    payload = dict(data)
    _validate_freight_payload(payload)
    booking_no = _legacy_create_booking(payload, user)
    sync_booking_master_ids(
        booking_no,
        customer_id=payload.get("customer_id"),
        sales_id=payload.get("sales_id"),
    )
    return booking_no


def update_booking_ssot(booking_no: str, data: Dict[str, Any], tenant_id: str | None = None) -> bool:
    payload = dict(data)
    _validate_freight_payload(payload)
    updated = _legacy_update_booking(booking_no, payload, tenant_id)
    if updated:
        sync_booking_master_ids(
            booking_no,
            customer_id=payload.get("customer_id"),
            sales_id=payload.get("sales_id"),
        )
    return updated
