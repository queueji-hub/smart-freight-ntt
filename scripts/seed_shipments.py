"""Seed shipment data from the user's cross-border export Excel file.

Run from project root:
    python -m scripts.seed_shipments
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
from database.connection import init_database, get_connection


def parse_date(s):
    """Parse DD/MM/YYYY or D/M/YYYY into ISO date string."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        parts = s.split("/")
        if len(parts) == 3:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            return date(y, m, d).isoformat()
    except (ValueError, TypeError):
        return None
    return None


# (job_no, booking_no, brand, combine, pick_up, stuffing, return_d,
#  container_no, seal_no, carrier, pod, size, bl, status, invoice_no, remark)
DATA = [
    ("SE25020604", "AKC0423430", "MARLBORO", "", "24/3/2025", "25/3/2025", "26/3/2025",
     "", "", "ANL-ATLANTIC GATE", "DILI,TIMOR", "1x20'GP", "✘ Not yet", "Finished",
     "IV00135", "-"),
    ("SE25030193", "THD1325353", "MARLBORO", "MDS BOARD ครึ่งตู้", "24/3/2025",
     "25/3/2025", "26/3/2025", "FSCU8065563", "R7801749", "CMA", "MALE",
     "1x40'HQ", "✘ Not yet", "Finished", "IV00137", ""),
    ("SE25030245", "250443837", "MARLBORO", "NO", "25/3/2025", "26/3/2025",
     "27/3/2025", "MRKU3342130", "ML-TH1023637", "MAERSK", "BENGHAZI, LIBYA",
     "1x40'GP", "✘ Not yet", "Finished", "IV00138", ""),
    ("SE25030198", "GLGSIN240754", "NO", "NO", "28/2/2025", "1/3/2025",
     "2/3/2025", "GESU6253696", "LGCL012840", "", "SIN", "1x40'HC",
     "✓ Issued", "Finished", "IV00133", ""),
    ("SE25030197", "GLGSIN240755", "NO", "NO", "1/3/2025", "3/3/2025",
     "4/3/2025", "GESU6186258", "LGCL012632", "", "SIN", "1x40'HC",
     "✓ Issued", "Finished", "IV00133", ""),
    ("SE25030196", "GLGSIN240756", "MARLBORO , MANCHESTER", "NO", "1/3/2025",
     "4/3/2025", "5/3/2025", "GESU6921711", "LGCL012633", "", "SIN", "1x40'HC",
     "✓ Issued", "Finished", "IV00133", ""),
    ("SE25030194", "GLGSIN240752", "MARLBORO , MANCHESTER", "NO", "3/3/2025",
     "5/3/2025", "6/3/2025", "GESU6358779", "LGCL012790", "", "SIN", "1x40'HC",
     "✓ Issued", "Finished", "IV00133", ""),
    ("SE25030334", "GLGSIN240769", "ESSE", "Floor Tile 300x300mm", "3/3/2025",
     "4/3/2025", "6/3/2025", "CRSU1375878", "LGCL012744", "", "SIN", "1x20'GP",
     "✓ Issued", "Finished", "IV00133", ""),
    ("SE25030199", "250664212", "NO", "ALUMINIUM DOOR", "3/3/2025", "4/3/2025",
     "5/3/2025", "TTNU1092355", "ML-TH1032275", "", "", "1x20'GP",
     "✘ Not yet", "In-Progress", "IV00155", ""),
    ("SE25030335", "BKK500347200", "NO", "CLOTHES / General Goods", "4/3/2025",
     "5/3/2025", "7/3/2025", "MAUU3004755", "SF0652535", "MMP (PIL)",
     "SYDNEY", "1x40'HC", "✓ Issued", "SOC", "IV00136", "SOC"),
    ("SE25030371", "APTLCBSIN250300126", "MEVIUS , MARLBORO", "CIGARETTES+CLOTHES",
     "6/3/2025", "7/3/2025", "8/3/2025", "APSU4213914", "APS014938",
     "MMP (ALPINE)", "SIN", "1x40'HC", "✓ Issued", "In-Progress",
     "IV00140", ""),
    ("SE25030372", "SNKO190250300522", "DAVIDOFF", "NO", "7/3/2025", "8/3/2025",
     "9/3/2025", "SKHU6482346", "SKLCH010953", "MMP (SINOKOR)", "INCHEON",
     "1x40'HC", "✓ Issued", "In-Progress", "IV00139", ""),
    ("SE25030336", "251047672", "-", "-", "7/3/2025", "7/3/2025", "7/3/2025",
     "MRSU3041566", "ML-TH1022725", "", "INCHEON", "1x40'HC", "✘ Not yet",
     "Cancelled", "IV00157", "มีค่า CANCEL รถ (จ่ายรถ - เก็บ ลค)"),
    ("SE25030435", "250694702", "LAMBERT & BUTLER", "NO", "11/3/2025",
     "12/3/2025", "13/3/2025", "MRKU5622736", "ML-TH1033208", "", "",
     "1x40'HC", "✘ Not yet", "Finished", "IV00154",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25030436", "251050456", "NO", "NO", "11/3/2025", "12/3/2025", "13/3/2025",
     "SUDU1984732", "ML-TH1029777", "", "", "1x20'GP", "✘ Not yet",
     "Finished", "IV00158", "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25030433", "APTLCBSIN250300164", "ESSE, CARNIVAL", "NO", "11/3/2025",
     "12/3/2025", "13/3/2025", "APSU4213940", "APS014922", "", "SIN",
     "1x40'HC", "✓ Issued", "Finished", "IV00141",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25030432", "251232455", "ESSE, CARNIVAL, ORLEANS", "NO", "12/3/2025",
     "13/3/2025", "14/3/2025", "MSKU0194848", "ML-TH1042938", "", "",
     "1x40'HC", "✘ Not yet", "Finished", "IV00159",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25030431", "251150176", "NO", "NO", "12/3/2025", "13/3/2025", "14/3/2025",
     "MRKU9660035", "ML-TH1028720", "", "", "1x20'GP", "✘ Not yet",
     "Finished", "IV00160", "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040092", "THD1335851", "MANCHESTER", "MDS BOARD", "15/3/2025",
     "17/3/2025", "18/3/2025", "CMAU5829663", "R7641825", "", "MALE",
     "1x40'HC", "✓ Issued", "Finished", "IV00147",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040093", "HASLS22250301391", "", "", "18/3/2025", "19/3/2025",
     "20/3/2025", "SKLU1911718", "HAL492212", "MULTIBOX // HEUNG-A",
     "CHENNAI, ICD BANGALORE", "1x20'GP", "✓ Issued", "Finished",
     "IV00182", "มี ROB LCB"),
    ("SE25040094", "251229940", "ESSE & DUNHILL", "", "19/3/2025", "20/3/2025",
     "21/3/2025", "CAAU8262182", "ML-TH1001226", "MAERSK", "SINGAPORE",
     "1x40'HC", "✘ Not yet", "Finished", "IV00166",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040195", "DOL2503004", "NO", "NO", "20/3/2025", "22/3/2025",
     "23/3/2025", "CRXU1630677", "SSL012249", "", "SIN", "1x20'GP",
     "✓ Issued", "Finished", "IV00148",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040199", "COAU7258206940", "NO", "NO", "22/3/2025", "24/3/2025",
     "25/3/2025", "CSNU7744658", "30326790", "COSCO", "HONG KONG",
     "1x40'HC", "✓ Issued", "Finished", "IV00149",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040197", "GLGJEA240814", "B&H", "NO", "22/3/2025", "24/3/2025",
     "25/3/2025", "BMOU5252096", "LGCL012797", "", "JEBEL ALI", "1x40'HC",
     "✓ Issued", "Finished", "IV00165",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040259", "VASBKK2500644", "MARLBORO, FUMER BOUCHE", "", "25/3/2025",
     "26/3/2025", "27/3/2025", "VMLU4227652", "GTCL040053", "GOODRICH",
     "SIN", "1x40'HC", "✓ Issued", "Finished", "IV00161",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040201", "VASBKK2500645", "NO", "NO", "25/3/2025", "26/3/2025",
     "27/3/2025", "VMLU3902611", "GTCL040060", "GOODRICH", "SIN",
     "1x40'HC", "✓ Issued", "Finished", "IV00161",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040202", "VASBKK2500646", "NO", "NO", "25/3/2025", "26/3/2025",
     "27/3/2025", "VMLU4233017", "GTCL040059", "GOODRICH", "SIN",
     "1x40'HC", "✓ Issued", "Finished", "IV00161",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040204", "VASBKK2500647", "DUNHILL", "NO", "25/3/2025", "26/3/2025",
     "27/3/2025", "VMLU3813788", "GTCL040055", "GOODRICH", "SIN",
     "1x20'GP", "✓ Issued", "Finished", "IV00161",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040260", "GTD0930503", "CANCEL", "", "28/3/2025", "", "31/3/2025",
     "TEMU8515137", "R7703403", "", "", "", "✘ Not yet", "Cancelled",
     "IV00175", "ลค cancel รับตู้ ศ คืน จ ติดวันอาทิตย์"),
    ("SE25040265", "GTD0930888", "NO", "", "28/3/2025", "30/3/2025",
     "31/3/2025", "TCLU8536770", "R7703416", "", "", "", "✘ Not yet",
     "In-Progress", "IV00176", "ตกเรือ"),
    ("SE25040263", "GTD0930885", "NO", "", "28/3/2025", "30/3/2025",
     "31/3/2025", "MAGU5743425", "R7703401", "", "", "", "✘ Not yet",
     "In-Progress", "IV00177", "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25040261", "GTD0930512", "NO", "", "29/3/2025", "30/3/2025",
     "31/3/2025", "GESU6772726", "R7703402", "", "", "", "✘ Not yet",
     "In-Progress", "IV00178", "ตกเรือ"),
    ("SE25040266", "ALCICPO66N30315", "", "", "31/3/2025", "1/4/2025",
     "2/4/2025", "AXEU6024716", "ASL2725852", "FUJITRANS", "INCHEON",
     "1x40'HC", "✓ Issued", "Finished", "IV00174",
     "ยกเลิกส่งออก ตู้อยู่ที่แหลมฉบัง"),
    ("SE25050075", "6414410300", "", "", "8/4/2025", "9/4/2025", "10/4/2025",
     "BMOU1645665", "30333317", "COSCO", "APAPA, NIGERIA", "1x20'GP",
     "✓ Issued", "Finished", "IV00185", ""),
    ("SE25050077", "CSXB25LCHSIN016159", "", "", "9/4/2025", "10/4/2025",
     "11/4/2025", "TGCU2310494", "CSX241894", "GLOBAL", "SIN", "1x20'GP",
     "✓ Issued", "Finished", "IV00183", ""),
    ("SE25050207", "THD1348169", "NO", "TISSUE PAPER 22 CARTONS", "22/4/2025",
     "23/4/2025", "24/4/2025", "TCNU2676392", "R7793418", "", "", "",
     "✘ Not yet", "Finished", "IV00192",
     "มีค่า C/O เพิ่ม $350 USD / CONT."),
    ("SE25050208", "252957036", "NO", "", "22/4/2025", "23/4/2025", "24/4/2025",
     "MRSU3912343", "ML-TH1041443", "", "", "", "✘ Not yet", "Finished",
     "IV00193", ""),
    ("SE25050279", "B-4184/25", "", "", "25/4/2025", "26/4/2025", "27/4/2025",
     "EMCU6013722", "CSX240913", "INFINITY", "SIN", "1x20'GP", "✓ Issued",
     "Finished", "IV00189", ""),
    ("SE25050310", "ALCICAQ05N40282", "NO", "", "3/5/2025", "4/5/2025",
     "5/5/2025", "TCNU8211690", "2732181", "FUJITRANS", "INCHEON",
     "1x40'HC", "✓ Issued", "In-Progress", "IV00195", ""),
    ("SE25050441", "AKC0428814", "NO", "", "9/5/2025", "9/5/2025", "10/5/2025",
     "CMAU0407156", "R7821503", "CMA", "MOTUKEA, ISLAND", "1x20'GP",
     "✘ Not yet", "In-Progress", "IV00201", "ลากคืนกรุงเทพ // ตกเรือ"),
    ("SE25050443", "THD1354603", "DUNHIL", "", "8/5/2025", "9/5/2025",
     "10/5/2025", "TCLU6702846", "R7624007", "CMA", "JEBEL", "1x40'GP",
     "✘ Not yet", "In-Progress", "IV00202", ""),
    ("SE25050436", "253418136", "NO", "", "6/5/2025", "8/5/2025", "9/5/2025",
     "MRSU3600685", "ML-TH1050053", "", "", "", "✘ Not yet", "In-Progress",
     "IV00196", ""),
    ("SE25050438", "253418658", "NO", "", "6/5/2025", "7/5/2025", "8/5/2025",
     "MRSU3715597", "ML-TH1051285", "", "", "", "✘ Not yet", "In-Progress",
     "IV00198", ""),
    ("SE25050439", "253424492", "FUMA PROVOKA, Marlboro", "", "7/5/2025",
     "10/5/2025", "11/5/2025", "MSKU1198107", "ML-TH1051364", "", "", "",
     "✘ Not yet", "In-Progress", "IV00199", ""),
    ("SE25050522", "FCLS2505007", "NO", "", "13/5/2025", "14/5/2025",
     "15/5/2025", "ZXJU0149242", "C40355", "INFINITY", "SIN", "",
     "✓ Issued", "In-Progress", "IV00205", ""),
    ("SE25050523", "ALCICPO68N50163", "NO", "", "19/5/2025", "20/5/2025",
     "21/5/2025", "NLLU4228392", "ASL2725579", "FUJITRANS", "INCHEON", "",
     "✓ Issued", "In-Progress", "IV00206", ""),
    ("SE25050524", "254001581", "Marlboro", "water", "20/5/2025", "21/5/2025",
     "22/5/2025", "MRKU2888810", "TH1087478", "", "", "", "✘ Not yet",
     "In-Progress", "IV00207", ""),
    ("SE25050525", "BKKFF8183800", "Marlboro", "chair", "21/5/2025",
     "22/5/2025", "23/5/2025", "MAUU1008767", "THBE66186", "CITY OCEAN",
     "NEW YORK, U.S.A", "", "✓ Issued", "SOC", "IV00211",
     "มีค่า C/O เพิ่ม $350 USD / CONT. - SOC // FULL UNDER TABLE"),
]


def main():
    init_database()
    
    inserted = 0
    skipped = 0
    
    with get_connection() as conn:
        for row in DATA:
            (job_no, booking_no, brand, combine, pick_up, stuffing, return_d,
             container_no, seal_no, carrier, pod, size, bl, status,
             invoice_no, remark) = row
            
            # Skip if already exists
            existing = conn.execute(
                "SELECT id FROM shipments WHERE job_no=?", (job_no,)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            
            conn.execute("""
                INSERT INTO shipments (
                    job_no, job_type, booking_no, brand,
                    combine_commodity, pick_up_date, stuffing_date, return_date,
                    container_no, seal_no, carrier, pol, pod, container_size,
                    bl_status, status, invoice_no, remark
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                job_no, "SE", booking_no, brand,
                combine, parse_date(pick_up), parse_date(stuffing),
                parse_date(return_d), container_no, seal_no, carrier,
                "Laem Chabang", pod, size, bl, status, invoice_no, remark,
            ))
            inserted += 1
    
    print(f"✅ Inserted: {inserted} shipments")
    print(f"⏭️  Skipped (already exist): {skipped}")
    print(f"📦 Total in DATA: {len(DATA)}")


if __name__ == "__main__":
    main()
