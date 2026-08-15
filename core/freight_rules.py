"""Canonical shipment handling rules shared by UI, managers and documents."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class FreightProfile:
    transport: str
    cargo_type: str
    volume_kind: str
    receiving_kind: str
    show_container_type: bool
    show_weight: bool
    show_cbm: bool
    show_chargeable_weight: bool
    show_cy: bool
    show_cfs: bool
    show_container_return: bool
    show_vessel: bool

def _norm(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "_")

def get_freight_profile(mode: Any, cargo_type: Any = "") -> FreightProfile:
    """Return one canonical profile for a shipment mode/cargo combination."""
    transport = _norm(mode)
    cargo = _norm(cargo_type)
    if transport in {"SEA", "SE", "SI", "OCEAN"} and cargo == "FCL":
        return FreightProfile("SEA", "FCL", "CONTAINER", "CY", True, True, False, False, True, False, True, True)
    if transport in {"SEA", "SE", "SI", "OCEAN"} and cargo == "LCL":
        return FreightProfile("SEA", "LCL", "CBM", "CFS", False, True, True, False, False, True, False, True)
    if transport in {"AIR", "AE", "AI"}:
        return FreightProfile("AIR", "AIR", "KG", "CFS", False, True, False, True, False, True, False, False)
    if transport in {"TRUCK", "TE", "TI", "ROAD"} and cargo == "FTL":
        return FreightProfile("TRUCK", "FTL", "TRUCK", "CFS", False, True, False, False, False, True, False, False)
    if transport in {"TRUCK", "TE", "TI", "ROAD"}:
        return FreightProfile("TRUCK", "LTL", "CBM", "CFS", False, True, True, False, False, True, False, False)
    return FreightProfile(transport or "SEA", cargo or "LCL", "CBM", "CFS", False, True, True, False, False, True, False, transport in {"SEA", "SE", "SI", "OCEAN"})

def resolve_vessel(mother_vessel: Any, vessel: Any) -> str:
    """Use Mother Vessel when present, otherwise fall back to Vessel."""
    return str(mother_vessel or vessel or "").strip()
