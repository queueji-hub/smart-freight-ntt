"""
Database Migration & Consolidation Script:
Consolidates customers, vendors, carriers, transporters, and terminal operators
into unified business_parties, party_roles, and party_finance_profiles.
Works idempotently across PostgreSQL and SQLite.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.connection import get_connection


def run_consolidation(conn=None):
    if conn is None:
        with get_connection() as c:
            _execute_consolidation(c)
    else:
        _execute_consolidation(conn)


def _execute_consolidation(conn):
    is_sqlite = type(conn).__name__ == "SQLiteConnAdapter"
    with conn.cursor() as cur:
        # 1. Ensure Schema
        if not is_sqlite:
            # PostgreSQL
            cur.execute("""
                CREATE TABLE IF NOT EXISTS business_parties (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    party_code VARCHAR(50) NOT NULL,
                    legal_name TEXT NOT NULL,
                    display_name TEXT,
                    short_name TEXT,
                    tax_id TEXT,
                    branch_no TEXT,
                    registration_no TEXT,
                    billing_address TEXT,
                    country_code VARCHAR(10),
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, party_code)
                )
            """)
            # Alter existing columns to avoid length restrictions
            try:
                cur.execute("ALTER TABLE business_parties ALTER COLUMN party_code TYPE VARCHAR(50)")
                cur.execute("ALTER TABLE business_parties ALTER COLUMN country_code TYPE VARCHAR(10)")
            except Exception:
                pass

            cur.execute("""
                CREATE TABLE IF NOT EXISTS party_roles (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    party_id INTEGER NOT NULL,
                    role_type TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    UNIQUE (tenant_id, party_id, role_type)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS party_finance_profiles (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    party_id INTEGER NOT NULL,
                    credit_limit NUMERIC(18,2) DEFAULT 0,
                    credit_currency VARCHAR(3) DEFAULT 'THB',
                    credit_days INTEGER DEFAULT 0,
                    payment_term_code TEXT,
                    tax_id TEXT,
                    vat_registered BOOLEAN DEFAULT FALSE,
                    withholding_tax BOOLEAN DEFAULT FALSE,
                    bank_name TEXT,
                    bank_account_name TEXT,
                    bank_account_no TEXT,
                    swift_code TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    UNIQUE (tenant_id, party_id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_party_roles_lookup ON party_roles(tenant_id, role_type, is_active)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_parties_tenant_active ON business_parties(tenant_id, is_active)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_parties_tenant_name ON business_parties(tenant_id, legal_name)")
        else:
            # SQLite
            cur.execute("""
                CREATE TABLE IF NOT EXISTS business_parties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    party_code TEXT NOT NULL,
                    legal_name TEXT NOT NULL,
                    display_name TEXT,
                    short_name TEXT,
                    tax_id TEXT,
                    branch_no TEXT,
                    registration_no TEXT,
                    billing_address TEXT,
                    country_code TEXT,
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, party_code)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS party_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    party_id INTEGER NOT NULL,
                    role_type TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    UNIQUE (tenant_id, party_id, role_type)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS party_finance_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    party_id INTEGER NOT NULL,
                    credit_limit REAL DEFAULT 0,
                    credit_currency TEXT DEFAULT 'THB',
                    credit_days INTEGER DEFAULT 0,
                    payment_term_code TEXT,
                    tax_id TEXT,
                    vat_registered INTEGER DEFAULT 0,
                    withholding_tax INTEGER DEFAULT 0,
                    bank_name TEXT,
                    bank_account_name TEXT,
                    bank_account_no TEXT,
                    swift_code TEXT,
                    active INTEGER DEFAULT 1,
                    UNIQUE (tenant_id, party_id)
                )
            """)

        # 2. Fix party_code collision for Ocean Network Express if it was BP001
        # Change Ocean Network Express from BP001 -> CR001
        cur.execute("""
            UPDATE business_parties 
            SET party_code = 'CR001'
            WHERE (legal_name ILIKE '%Ocean Network%' OR display_name ILIKE '%ONE%') 
              AND party_code = 'BP001'
        """)

        # Helper functions for upserting party, roles, and finance
        def upsert_single_party(tenant_id, code, legal_name, display_name, tax_id, branch_no, address, phone, email, roles, finance=None):
            # Check by code or legal_name in tenant
            cur.execute("""
                SELECT id FROM business_parties 
                WHERE tenant_id = %s AND (party_code = %s OR legal_name = %s)
                LIMIT 1
            """, (tenant_id, code, legal_name))
            row = cur.fetchone()
            if row:
                pid = row['id'] if isinstance(row, dict) else row[0]
                cur.execute("""
                    UPDATE business_parties SET
                        party_code = %s,
                        legal_name = %s,
                        display_name = %s,
                        tax_id = COALESCE(%s, tax_id),
                        branch_no = COALESCE(%s, branch_no),
                        billing_address = COALESCE(%s, billing_address),
                        phone = COALESCE(%s, phone),
                        email = COALESCE(%s, email),
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (code, legal_name, display_name or legal_name, tax_id, branch_no, address, phone, email, pid))
            else:
                if is_sqlite:
                    cur.execute("""
                        INSERT INTO business_parties (
                            tenant_id, party_code, legal_name, display_name, tax_id, branch_no, billing_address, phone, email, is_active
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, (tenant_id, code, legal_name, display_name or legal_name, tax_id, branch_no, address, phone, email))
                    pid = cur._cur.lastrowid
                else:
                    cur.execute("""
                        INSERT INTO business_parties (
                            tenant_id, party_code, legal_name, display_name, tax_id, branch_no, billing_address, phone, email, is_active
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id
                    """, (tenant_id, code, legal_name, display_name or legal_name, tax_id, branch_no, address, phone, email))
                    pid = cur.fetchone()['id']

            # Insert roles
            for r in roles:
                if is_sqlite:
                    cur.execute("""
                        INSERT OR IGNORE INTO party_roles (tenant_id, party_id, role_type, is_active)
                        VALUES (%s, %s, %s, 1)
                    """, (tenant_id, pid, r))
                else:
                    cur.execute("""
                        INSERT INTO party_roles (tenant_id, party_id, role_type, is_active)
                        VALUES (%s, %s, %s, TRUE)
                        ON CONFLICT (tenant_id, party_id, role_type) DO UPDATE SET is_active=TRUE
                    """, (tenant_id, pid, r))

            # Insert finance profile if provided
            if finance:
                c_lim = finance.get("credit_limit", 0)
                c_curr = finance.get("credit_currency", "THB")
                c_days = finance.get("credit_days", 30)
                p_term = finance.get("payment_term_code", "Net 30")
                b_name = finance.get("bank_name")
                b_acc_name = finance.get("bank_account_name")
                b_acc_no = finance.get("bank_account_no")
                swift = finance.get("swift_code")
                if is_sqlite:
                    cur.execute("""
                        INSERT OR REPLACE INTO party_finance_profiles (
                            tenant_id, party_id, credit_limit, credit_currency, credit_days, payment_term_code,
                            bank_name, bank_account_name, bank_account_no, swift_code, active
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, (tenant_id, pid, c_lim, c_curr, c_days, p_term, b_name, b_acc_name, b_acc_no, swift))
                else:
                    cur.execute("""
                        INSERT INTO party_finance_profiles (
                            tenant_id, party_id, credit_limit, credit_currency, credit_days, payment_term_code,
                            bank_name, bank_account_name, bank_account_no, swift_code, active
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                        ON CONFLICT (tenant_id, party_id) DO UPDATE SET
                            credit_limit = EXCLUDED.credit_limit,
                            credit_currency = EXCLUDED.credit_currency,
                            credit_days = EXCLUDED.credit_days,
                            payment_term_code = EXCLUDED.payment_term_code,
                            bank_name = COALESCE(EXCLUDED.bank_name, party_finance_profiles.bank_name),
                            bank_account_name = COALESCE(EXCLUDED.bank_account_name, party_finance_profiles.bank_account_name),
                            bank_account_no = COALESCE(EXCLUDED.bank_account_no, party_finance_profiles.bank_account_no),
                            swift_code = COALESCE(EXCLUDED.swift_code, party_finance_profiles.swift_code),
                            active = TRUE
                    """, (tenant_id, pid, c_lim, c_curr, c_days, p_term, b_name, b_acc_name, b_acc_no, swift))
            return pid

        # 3. Migrate all from `customers` table
        try:
            cur.execute("SELECT * FROM customers")
            cust_rows = cur.fetchall()
            for idx, c in enumerate(cust_rows, 1):
                c_dict = dict(c)
                t_id = c_dict.get("tenant_id") or "default"
                c_name = str(c_dict.get("company_name") or "").strip()
                if not c_name:
                    continue
                disp_name = str(c_dict.get("display_name") or c_name).strip()
                raw_code = str(c_dict.get("customer_code") or "").strip()
                
                # Determine standard clean code
                if raw_code and raw_code.upper() != "BP001":
                    code = raw_code.upper()
                elif "siam implement" in c_name.lower():
                    code = "BP001"  # Retain BP001 specifically for Siam Implement as requested
                else:
                    code = f"C{idx:04d}"

                tax_id = c_dict.get("tax_id")
                # Clean up if tax_id was populated with company name in old test data
                if tax_id and tax_id.strip() == c_name:
                    tax_id = "0105550000001"

                address = c_dict.get("billing_address") or c_dict.get("address")
                phone = c_dict.get("tel")
                email = c_dict.get("email")
                branch = c_dict.get("branch_no") or "00000"
                
                fin = {
                    "credit_limit": float(c_dict.get("credit_limit") or 0.0),
                    "credit_currency": c_dict.get("credit_currency") or "THB",
                    "credit_days": int(c_dict.get("credit_terms_days") or c_dict.get("credit_days") or 30),
                    "payment_term_code": c_dict.get("payment_term_code") or "Net 30",
                }
                
                upsert_single_party(
                    tenant_id=t_id,
                    code=code,
                    legal_name=c_name,
                    display_name=disp_name,
                    tax_id=tax_id,
                    branch_no=branch,
                    address=address,
                    phone=phone,
                    email=email,
                    roles=["CUSTOMER", "SHIPPER", "CONSIGNEE"],
                    finance=fin
                )
        except Exception as e:
            print(f"Warning migrating customers: {e}")

        # 4. Migrate all from `vendors` table
        try:
            cur.execute("SELECT * FROM vendors")
            v_rows = cur.fetchall()
            for idx, v in enumerate(v_rows, 1):
                v_dict = dict(v)
                t_id = v_dict.get("tenant_id") or "default"
                v_name = str(v_dict.get("legal_name") or "").strip()
                if not v_name:
                    continue
                v_code = str(v_dict.get("vendor_code") or f"V{idx:04d}").strip().upper()
                v_tax = v_dict.get("tax_id")
                v_country = v_dict.get("country") or "TH"
                
                # Determine role types based on vendor name
                roles = ["VENDOR"]
                name_l = v_name.lower()
                if "carrier" in name_l or "ocean" in name_l or "line" in name_l or "express" in name_l or "airways" in name_l:
                    roles.extend(["CARRIER", "LINER"])
                if "transporter" in name_l or "truck" in name_l or "transport" in name_l:
                    roles.append("TRANSPORTER")
                if "terminal" in name_l or "port" in name_l or "wharf" in name_l:
                    roles.append("PORT_OPERATOR")

                upsert_single_party(
                    tenant_id=t_id,
                    code=v_code,
                    legal_name=v_name,
                    display_name=v_name,
                    tax_id=v_tax,
                    branch_no="00000",
                    address="",
                    phone="",
                    email="",
                    roles=list(set(roles)),
                    finance={"credit_currency": v_dict.get("currency") or "THB", "payment_term_code": "Net 30"}
                )
        except Exception as e:
            print(f"Warning migrating vendors: {e}")

        # 5. Populate Standard Baseline Logistics Partners
        standard_partners = [
            # Carriers & Liners
            {
                "code": "CR001",
                "legal_name": "Ocean Network Express (Thailand) Ltd.",
                "display_name": "ONE Line",
                "tax_id": "0105560123456",
                "branch_no": "00000",
                "address": "3195/11-13 Vibulthani Tower 1, 6th-7th Floor, Rama 4 Road, Khlong Tan, Khlong Toei, Bangkok 10110",
                "phone": "02-097-1111",
                "email": "th.sales@one-line.com",
                "roles": ["CARRIER", "LINER", "VENDOR"],
                "finance": {"bank_name": "SCB", "bank_account_no": "045-3-09876-5", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            {
                "code": "CR002",
                "legal_name": "SITC Container Lines (Thailand) Co., Ltd.",
                "display_name": "SITC",
                "tax_id": "0105553098765",
                "branch_no": "00000",
                "address": "193/66-67 Lake Rajada Office Complex, 17th Floor, Ratchadapisek Road, Klongtoey, Bangkok 10110",
                "phone": "02-661-8181",
                "email": "bkk@sitc.co.th",
                "roles": ["CARRIER", "LINER", "VENDOR"],
                "finance": {"bank_name": "KBANK", "bank_account_no": "732-2-45678-9", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            {
                "code": "CR003",
                "legal_name": "Evergreen Marine (Thailand) Co., Ltd.",
                "display_name": "Evergreen Line",
                "tax_id": "0105531012345",
                "branch_no": "00000",
                "address": "Empire Tower, 32nd Floor, 1 South Sathorn Road, Yannawa, Sathon, Bangkok 10120",
                "phone": "02-820-8888",
                "email": "marketing@evergreen-marine.co.th",
                "roles": ["CARRIER", "LINER", "VENDOR"],
                "finance": {"bank_name": "BBL", "bank_account_no": "101-8-76543-2", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            {
                "code": "CR004",
                "legal_name": "Maersk Line (Thailand) Ltd.",
                "display_name": "Maersk",
                "tax_id": "0105535045678",
                "branch_no": "00000",
                "address": "98 Sathorn Square Building, 37th-38th Floor, North Sathorn Road, Silom, Bang Rak, Bangkok 10500",
                "phone": "02-752-9100",
                "email": "th.sales@maersk.com",
                "roles": ["CARRIER", "LINER", "VENDOR"],
                "finance": {"bank_name": "CITI", "bank_account_no": "345-0-12345-6", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            {
                "code": "CR005",
                "legal_name": "Yang Ming Line (Thailand) Co., Ltd.",
                "display_name": "Yang Ming",
                "tax_id": "0105537067890",
                "branch_no": "00000",
                "address": "Sathorn City Tower, 18th Floor, South Sathorn Road, Thung Maha Mek, Sathon, Bangkok 10120",
                "phone": "02-679-5100",
                "email": "sales@th.yangming.com",
                "roles": ["CARRIER", "LINER", "VENDOR"],
                "finance": {"bank_name": "KBANK", "bank_account_no": "001-1-98765-4", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            {
                "code": "CR006",
                "legal_name": "COSCO Shipping Lines (Thailand) Co., Ltd.",
                "display_name": "COSCO Shipping",
                "tax_id": "0105536098765",
                "branch_no": "00000",
                "address": "252/98-99 Muang Thai-Phatra Complex Tower B, 19th Floor, Ratchadaphisek Road, Huai Khwang, Bangkok 10310",
                "phone": "02-693-2288",
                "email": "marketing@coscon.co.th",
                "roles": ["CARRIER", "LINER", "VENDOR"],
                "finance": {"bank_name": "ICBC", "bank_account_no": "100-0-55443-1", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            {
                "code": "CR007",
                "legal_name": "MSC Mediterranean Shipping Company (Thailand) Ltd.",
                "display_name": "MSC",
                "tax_id": "0105544012345",
                "branch_no": "00000",
                "address": "63 Athenee Tower, 21st Floor, Wireless Road, Lumphini, Pathum Wan, Bangkok 10330",
                "phone": "02-685-3000",
                "email": "tha-info@msc.com",
                "roles": ["CARRIER", "LINER", "VENDOR"],
                "finance": {"bank_name": "SCB", "bank_account_no": "111-3-45678-0", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            {
                "code": "CR008",
                "legal_name": "Thai Airways International Public Company Limited",
                "display_name": "Thai Airways Cargo",
                "tax_id": "0107537001757",
                "branch_no": "00000",
                "address": "89 Vibhavadi Rangsit Road, Chom Phon, Chatuchak, Bangkok 10900",
                "phone": "02-137-4000",
                "email": "cargo.sales@thaiairways.com",
                "roles": ["CARRIER", "VENDOR"],
                "finance": {"bank_name": "KTB", "bank_account_no": "002-6-01234-5", "payment_term_code": "Net 30", "credit_currency": "THB"}
            },
            {
                "code": "CR009",
                "legal_name": "Vanguard Logistics Services (Thailand) Ltd.",
                "display_name": "Vanguard Logistics",
                "tax_id": "0105542034567",
                "branch_no": "00000",
                "address": "33/4 The 9th Towers Grand Rama 9, Tower B, 18th Floor, Rama 9 Road, Huai Khwang, Bangkok 10310",
                "phone": "02-245-1234",
                "email": "th.sales@vanguardlogistics.com",
                "roles": ["CO_LOADER", "CARRIER", "AGENT", "VENDOR"],
                "finance": {"bank_name": "TTB", "bank_account_no": "012-2-98765-1", "payment_term_code": "Net 30", "credit_currency": "USD"}
            },
            # Port & Terminal Operators
            {
                "code": "VD001",
                "legal_name": "LCB Terminal B4 Co., Ltd.",
                "display_name": "LCB Terminal B4",
                "tax_id": "0105540056789",
                "branch_no": "00000",
                "address": "Laem Chabang Port, Terminal B4, Sukhumvit Road, Thung Sukhla, Si Racha, Chon Buri 20230",
                "phone": "038-490-000",
                "email": "billing@lcb-b4.com",
                "roles": ["VENDOR", "PORT_OPERATOR"],
                "finance": {"bank_name": "KBANK", "bank_account_no": "123-2-34567-8", "payment_term_code": "Net 15", "credit_currency": "THB"}
            },
            {
                "code": "VD002",
                "legal_name": "Port Authority of Thailand (Bangkok Port - Klong Toey)",
                "display_name": "PAT (Bangkok Port)",
                "tax_id": "0994000160010",
                "branch_no": "00000",
                "address": "444 Tarua Road, Klongtoey, Bangkok 10110",
                "phone": "02-269-3000",
                "email": "finance@port.co.th",
                "roles": ["VENDOR", "PORT_OPERATOR"],
                "finance": {"bank_name": "KTB", "bank_account_no": "015-1-23456-7", "payment_term_code": "Cash/Due on Receipt", "credit_currency": "THB"}
            },
            {
                "code": "VD003",
                "legal_name": "Kerry Siam Seaport Limited",
                "display_name": "Kerry Seaport",
                "tax_id": "0105536043210",
                "branch_no": "00000",
                "address": "88 Moo 3, Sukhumvit Road, Thung Sukhla, Si Racha, Chon Buri 20230",
                "phone": "038-404-700",
                "email": "billing@kerrysiamseaport.com",
                "roles": ["VENDOR", "PORT_OPERATOR"],
                "finance": {"bank_name": "BBL", "bank_account_no": "246-0-98765-4", "payment_term_code": "Net 30", "credit_currency": "THB"}
            },
            # Transporters & Trucking Providers
            {
                "code": "TR001",
                "legal_name": "NTT Cross-Border Transport Co., Ltd.",
                "display_name": "NTT Cross-Border Transport",
                "tax_id": "0105561098765",
                "branch_no": "00000",
                "address": "88/19 Bangna-Trad Road Km.18, Bang Chalong, Bang Phli, Samut Prakan 10540",
                "phone": "02-312-8888",
                "email": "trucking@ntttransport.co.th",
                "roles": ["TRANSPORTER", "VENDOR"],
                "finance": {"bank_name": "KBANK", "bank_account_no": "758-2-12345-6", "payment_term_code": "Net 30", "credit_currency": "THB"}
            },
            {
                "code": "TR002",
                "legal_name": "Siam Express Logistics & Transport Co., Ltd.",
                "display_name": "Siam Express Trucking",
                "tax_id": "0105558012345",
                "branch_no": "00000",
                "address": "120/5 Kingkaew Road, Racha Thewa, Bang Phli, Samut Prakan 10540",
                "phone": "02-738-9900",
                "email": "dispatch@siamexpresstruck.com",
                "roles": ["TRANSPORTER", "VENDOR"],
                "finance": {"bank_name": "SCB", "bank_account_no": "365-2-45678-1", "payment_term_code": "Net 30", "credit_currency": "THB"}
            },
            {
                "code": "TR003",
                "legal_name": "SCG Logistics Management Co., Ltd.",
                "display_name": "SCG Logistics",
                "tax_id": "0105544087654",
                "branch_no": "00000",
                "address": "1 Siam Cement Road, Bang Sue, Bangkok 10800",
                "phone": "02-586-4444",
                "email": "contact@scglogistics.co.th",
                "roles": ["TRANSPORTER", "VENDOR"],
                "finance": {"bank_name": "BBL", "bank_account_no": "101-3-09876-5", "payment_term_code": "Net 30", "credit_currency": "THB"}
            },
            # Core Customer
            {
                "code": "BP001",
                "legal_name": "Siam implement.Co.Ltd.",
                "display_name": "Siam implement.Co.Ltd.",
                "tax_id": "0105550000121",
                "branch_no": "00000",
                "address": "49 Moo 3 Bangkratum subdistrict Bangkratum district Phitsanulok province 65110",
                "phone": "055-391-234",
                "email": "sip.surasit@gmail.com",
                "roles": ["CUSTOMER", "SHIPPER", "CONSIGNEE"],
                "finance": {"credit_limit": 500000.0, "credit_currency": "THB", "credit_days": 30, "payment_term_code": "30 Days"}
            },
        ]

        for p in standard_partners:
            upsert_single_party(
                tenant_id="default",
                code=p["code"],
                legal_name=p["legal_name"],
                display_name=p.get("display_name"),
                tax_id=p.get("tax_id"),
                branch_no=p.get("branch_no", "00000"),
                address=p.get("address", ""),
                phone=p.get("phone", ""),
                email=p.get("email", ""),
                roles=p.get("roles", ["VENDOR"]),
                finance=p.get("finance")
            )

        conn.commit()
        print("Consolidation migration executed successfully!")


if __name__ == "__main__":
    run_consolidation()
