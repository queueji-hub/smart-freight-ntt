"""Presentation helpers for Booking UI and documents.

These helpers are deterministic and side-effect free so the UI and PDF layers can
share the same wording and visibility rules without touching database/business logic.
"""
from __future__ import annotations

from typing import Any, Iterable

from core.freight_rules import FreightProfile, get_freight_profile, resolve_vessel

CONTAINER_TYPES: tuple[str, ...] = (
    "20'GP",
    "40'GP",
    "40'HC",
    "45'HC",
    "20'OT",
    "40'OT",
    "20'FR",
    "40'FR",
)


def booking_profile(data: dict[str, Any]) -> FreightProfile:
    """Resolve the canonical freight profile from a booking payload."""
    mode = data.get("mode") or data.get("transport") or data.get("job_type")
    cargo = data.get("cargo_type") or data.get("cargo") or data.get("service_type")
    return get_freight_profile(mode, cargo)


def vessel_display(data: dict[str, Any]) -> str:
    """Display Mother Vessel when present, otherwise Vessel."""
    return resolve_vessel(data.get("mother_vessel") or data.get("m_vessel"), data.get("vessel")) or "—"


def container_lines(items: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Normalize container planning rows into type/quantity pairs for UI/PDF."""
    result: list[dict[str, Any]] = []
    for row in items or []:
        kind = str(row.get("container_type") or row.get("type") or "").strip()
        if not kind:
            continue
        try:
            qty = int(float(row.get("quantity") or row.get("qty") or 0))
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        result.append({"container_type": kind, "quantity": qty})
    return result


def applicable_fields(profile: FreightProfile) -> dict[str, bool]:
    """Return field visibility flags for a compact, rule-driven booking form."""
    return {
        "container_type": profile.show_container_type,
        "weight": profile.show_weight,
        "cbm": profile.show_cbm,
        "chargeable_weight": profile.show_chargeable_weight,
        "cy": profile.show_cy,
        "cfs": profile.show_cfs,
        "container_return": profile.show_container_return,
        "vessel": profile.show_vessel,
    }
