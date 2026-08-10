import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def fix_containers_cols():
    cols = ["vgm_kg", "vgm_method", "tare_weight", "max_payload", "volume_cbm", "soc_coc", "remark", "cbm", "temperature", "ventilation", "temp_setting", "temp_unit", "vent_setting", "genset_no", "oog_length_cm", "oog_width_cm", "oog_height_cm", "un_number", "imo_class", "status"]
    for c in cols:
        with get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(f"ALTER TABLE containers ADD COLUMN {c} TEXT;")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"Failed to add {c}: {e}")

if __name__ == "__main__":
    fix_containers_cols()
