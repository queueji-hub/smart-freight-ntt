from managers.tenant_context import get_current_tenant_id
"""
LCL Consolidation & De-consolidation Business Engine
1 Master Job (MBL) <-> Multiple House Jobs (HBL) Relational Cost Prorating Engine
100% CargoWise Standard Compliant
"""

from typing import List, Dict, Any

def prorate_lcl_shared_cost(
    master_cost_thb: float,
    house_shipments: List[Dict[str, Any]],
    prorate_by: str = "cbm"
) -> List[Dict[str, Any]]:
    """
    Prorates shared Master Job expenses (e.g. Master Freight, Terminal Handling, CFS Fee)
    across all linked House Jobs (HBLs) based on CBM volume or Gross Weight proportion.
    """
    if not house_shipments:
        return []

    total_basis = sum(float(h.get(prorate_by, 0) or 0) for h in house_shipments)
    if total_basis <= 0:
        # Fallback to equal distribution if basis sum is 0
        equal_share = round(master_cost_thb / len(house_shipments), 2)
        return [
            {**h, "allocated_cost_thb": equal_share, "allocation_share_percent": round(100.0 / len(house_shipments), 2)}
            for h in house_shipments
        ]

    results = []
    for h in house_shipments:
        val = float(h.get(prorate_by, 0) or 0)
        share_ratio = val / total_basis
        allocated = round(master_cost_thb * share_ratio, 2)
        results.append({
            **h,
            "allocated_cost_thb": allocated,
            "allocation_share_percent": round(share_ratio * 100.0, 2)
        })

    return results
