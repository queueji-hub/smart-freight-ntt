from managers.tenant_context import get_current_tenant_id
"""
Enterprise Container Management & Operational Gatekeeper Engine
CargoWise Standard Compliant — Auto-Calculations & Fast Batch Processing
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from database.connection import get_connection

# =========================================================
# CONTAINER SPECIFICATIONS & TARE MATRIX (CARGOWISE COMPLIANT)
# =========================================================
CONTAINER_SPECS = {
    "20GP": {"cbm": 33.2, "tare_kg": 2200, "payload_kg": 28200},
    "40GP": {"cbm": 67.7, "tare_kg": 3750, "payload_kg": 26730},
    "40HC": {"cbm": 76.4, "tare_kg": 3900, "payload_kg": 28600},
    "45HC": {"cbm": 86.0, "tare_kg": 4800, "payload_kg": 29600},
    "20RF": {"cbm": 28.3, "tare_kg": 3080, "payload_kg": 27400},
    "40RF": {"cbm": 67.3, "tare_kg": 4500, "payload_kg": 29500},
    "20OT": {"cbm": 32.5, "tare_kg": 2350, "payload_kg": 27800},
    "40OT": {"cbm": 65.5, "tare_kg": 3850, "payload_kg": 28150},
    "20FR": {"cbm": 27.9, "tare_kg": 2750, "payload_kg": 31000},
    "40FR": {"cbm": 54.8, "tare_kg": 5200, "payload_kg": 39000},
}


# =========================================================
# ISO 6346 CONTAINER NUMBER CHECKSUM VALIDATOR
# =========================================================
def validate_container_number(container_no: str) -> bool:
    """
    Validates container serial number according to ISO 6346 check digit algorithm.
    Returns True if format matches 4 letters + 7 digits and check digit is valid.
    """
    if not container_no or not isinstance(container_no, str):
        return False

    clean_no = re.sub(r'[^A-Z0-9]', '', container_no.strip().upper())
    if len(clean_no) != 11:
        return False

    char_map = {
        'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18, 'I': 19, 'J': 20,
        'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27, 'Q': 28, 'R': 29, 'S': 30, 'T': 31,
        'U': 32, 'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38
    }

    sum_val = 0
    for i in range(10):
        char = clean_no[i]
        val = char_map[char] if char in char_map else int(char)
        sum_val += val * (2 ** i)

    check_digit = (sum_val % 11) % 10
    actual_check_digit = int(clean_no[10])

    return check_digit == actual_check_digit


# =========================================================
# AUTO-CALCULATOR ENGINE
# =========================================================
def calculate_container_metrics(
    container_size: str,
    gross_weight: float = 0.0,
    net_weight: float = 0.0,
    tare_weight: float = 0.0,
    volume_cbm: float = 0.0
) -> Dict[str, Any]:
    """
    Calculates CBM, SOLAS VGM (Method 2), Volumetric Weights, and Capacity Utilization %.
    """
    spec = CONTAINER_SPECS.get(container_size.upper(), CONTAINER_SPECS["40HC"])
    
    calc_tare = tare_weight if tare_weight > 0 else spec["tare_kg"]
    calc_gross = gross_weight if gross_weight > 0 else (net_weight + calc_tare)
    vgm_kg = calc_gross + calc_tare if (gross_weight > 0 and net_weight == 0) else (gross_weight or (net_weight + calc_tare))

    cbm_utilization = (volume_cbm / spec["cbm"] * 100.0) if spec["cbm"] > 0 else 0.0
    weight_utilization = (gross_weight / spec["payload_kg"] * 100.0) if spec["payload_kg"] > 0 else 0.0

    return {
        "calculated_tare_kg": round(calc_tare, 2),
        "calculated_gross_kg": round(calc_gross, 2),
        "vgm_kg": round(vgm_kg, 2),
        "volumetric_weight_sea_kg": round(volume_cbm * 1000.0, 2),
        "volumetric_weight_air_kg": round(volume_cbm * 166.67, 2),
        "cbm_utilization_percent": round(min(cbm_utilization, 200.0), 1),
        "weight_utilization_percent": round(min(weight_utilization, 200.0), 1),
        "max_payload_kg": spec["payload_kg"],
        "max_cbm": spec["cbm"]
    }


# =========================================================
# ADD CONTAINER (SINGLE RECORD)
# =========================================================
def add_container(data: Dict[str, Any]) -> bool:
    """
    Inserts a container record into database with auto-calculated VGM and Tare metrics.
    """
    job_no = data.get("job_no")
    shipment_id = data.get("shipment_id")

    if not shipment_id and job_no:
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM shipments WHERE job_no=%s", (job_no,)).fetchone()
            if row:
                shipment_id = row['id']

    if not shipment_id:
        return False  # Cannot insert without shipment_id

    c_size = (data.get("container_size") or "40HC").upper()
    g_weight = float(data.get("gross_weight", 0) or 0)
    n_weight = float(data.get("net_weight", 0) or 0)
    t_weight = float(data.get("tare_weight", 0) or 0)
    vol_cbm = float(data.get("volume_cbm", data.get("volume", 0)) or 0)

    metrics = calculate_container_metrics(c_size, g_weight, n_weight, t_weight, vol_cbm)

    sql = """
        INSERT INTO containers (
            shipment_id, job_no, bl_no, container_no, container_size, container_type,
            seal_no, vgm_kg, vgm_method, gross_weight, net_weight,
            tare_weight, max_payload, volume_cbm, soc_coc,
            temp_setting, temp_unit, vent_setting, genset_no,
            oog_length_cm, oog_width_cm, oog_height_cm, un_number, imo_class, status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    params = (
        shipment_id,
        job_no,
        data.get("bl_no"),
        (data.get("container_no") or "").upper().strip(),
        c_size,
        data.get("container_type", "GP"),
        data.get("seal_no"),
        data.get("vgm_kg", metrics["vgm_kg"]),
        data.get("vgm_method", "Method 2"),
        metrics["calculated_gross_kg"],
        n_weight,
        metrics["calculated_tare_kg"],
        metrics["max_payload_kg"],
        vol_cbm,
        data.get("soc_coc", "COC"),
        data.get("temp_setting"),
        data.get("temp_unit", "C"),
        data.get("vent_setting"),
        data.get("genset_no"),
        float(data.get("oog_length_cm", 0) or 0),
        float(data.get("oog_width_cm", 0) or 0),
        float(data.get("oog_height_cm", 0) or 0),
        data.get("un_number"),
        data.get("imo_class"),
        data.get("status", "Loaded")
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return True


# =========================================================
# BATCH CONTAINER PARSER (FAST CS ENTRY)
# =========================================================
def parse_and_add_containers_batch(raw_text: str, job_no: str, bl_no: str = None) -> List[Dict[str, Any]]:
    """
    Parses multi-line text input into container records and inserts them into DB.
    Format examples:
    TCNU1234567 / SEAL987654 / 40HC / 24500 / 65.5
    MSKU9876543, SEAL1122, 20GP, 18000, 30.0
    """
    inserted = []
    lines = raw_text.strip().split("\n")

    for line in lines:
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#"):
            continue

        parts = [p.strip() for p in re.split(r'[/,;\t]', clean_line) if p.strip()]
        if not parts:
            continue

        cntr_no = parts[0].upper()
        seal_no = parts[1] if len(parts) > 1 else ""
        c_size = parts[2].upper() if len(parts) > 2 else "40HC"
        
        gw = 0.0
        cbm = 0.0

        if len(parts) > 3:
            try:
                gw = float(re.sub(r'[^0-9.]', '', parts[3]))
            except ValueError:
                gw = 0.0

        if len(parts) > 4:
            try:
                cbm = float(re.sub(r'[^0-9.]', '', parts[4]))
            except ValueError:
                cbm = 0.0

        payload = {
            "job_no": job_no,
            "bl_no": bl_no,
            "container_no": cntr_no,
            "seal_no": seal_no,
            "container_size": c_size,
            "gross_weight": gw,
            "volume_cbm": cbm
        }

        if add_container(payload):
            inserted.append(payload)

    return inserted


# =========================================================
# LIST CONTAINERS
# =========================================================
def list_containers(bl_no: str = None, job_no: str = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM containers WHERE 1=1"
    params = []

    if bl_no:
        sql += " AND LOWER(bl_no)=%s"
        params.append(bl_no.lower())

    if job_no:
        sql += " AND LOWER(job_no)=%s"
        params.append(job_no.lower())

    sql += " ORDER BY id ASC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]

# =========================================================
# DELETE CONTAINER
# =========================================================
def delete_container(container_id: int, job_no: str) -> bool:
    sql = "DELETE FROM containers WHERE id=%s AND job_no=%s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (container_id, job_no))
            conn.commit()
            return cur.rowcount > 0


# =========================================================
# GATEKEEPER INTEGRITY VALIDATOR
# =========================================================
def validate_job_readiness_for_billing(job_no: str) -> Tuple[bool, List[str]]:
    """
    Operational gatekeeper: Checks if container list, Seal numbers, and SOLAS VGM values
    are complete before allowing job billing / invoice generation or closure.
    """
    errors = []
    containers = list_containers(job_no=job_no)

    if not containers:
        errors.append("❌ No containers assigned to this job record.")
        return False, errors

    for idx, c in enumerate(containers, 1):
        c_no = c.get("container_no", "")
        seal_no = c.get("seal_no", "")
        vgm = float(c.get("vgm_kg", 0) or 0)

        if not c_no:
            errors.append(f"❌ Container #{idx}: Missing Container Serial Number.")
        elif not validate_container_number(c_no):
            errors.append(f"⚠️ Container #{idx} ({c_no}): Invalid ISO 6346 Checksum Digit.")

        if not seal_no:
            errors.append(f"❌ Container #{idx} ({c_no}): Missing Seal Number (Required for B/L & Manifest).")

        if vgm <= 0:
            errors.append(f"❌ Container #{idx} ({c_no}): Missing SOLAS Verified Gross Mass (VGM kg).")

    is_valid = len(errors) == 0
    return is_valid, errors