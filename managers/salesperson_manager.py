"""Salesperson Master: canonical CRUD for sales representatives."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id

_salesperson_schema_ensured = False


def _ensure_schema(conn) -> None:
    global _salesperson_schema_ensured
    if _salesperson_schema_ensured:
        return
    try:
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter"
            if is_sqlite:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS salespersons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT DEFAULT 'default',
                        sales_code TEXT,
                        name TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        commission_rate REAL DEFAULT 0,
                        remarks TEXT,
                        is_active INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS salespersons (
                        id SERIAL PRIMARY KEY,
                        tenant_id TEXT DEFAULT 'default',
                        sales_code VARCHAR(20),
                        name TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        commission_rate NUMERIC(5,2) DEFAULT 0,
                        remarks TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_salespersons_active ON salespersons(tenant_id, is_active)")
        try:
            conn.commit()
        except Exception:
            pass
        _salesperson_schema_ensured = True
    except Exception:
        pass


def list_salespersons(active_only: bool = False, user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            sales = []
            try:
                sql = """
                    SELECT id, tenant_id, sales_code, name, email, phone, commission_rate, remarks, is_active, created_at, updated_at
                    FROM salespersons
                    WHERE (tenant_id = %s OR tenant_id IS NULL OR tenant_id = 'default')
                """
                if active_only:
                    sql += " AND (is_active = TRUE OR is_active = 1)"
                sql += " ORDER BY sales_code ASC, name ASC"
                cur.execute(sql, (tenant,))
                sales = [dict(r) for r in cur.fetchall()]
            except Exception:
                pass

            # Also auto-seed/include users with sales role if not already present
            try:
                cur.execute("""
                    SELECT id, username, full_name, email, role
                    FROM users
                    WHERE LOWER(COALESCE(is_active::text, '0')) IN ('1','true','t')
                      AND LOWER(COALESCE(role, '')) IN ('sales','admin','manager')
                    ORDER BY LOWER(COALESCE(full_name, username))
                """)
                users = [dict(r) for r in cur.fetchall()]
                existing_codes = {str(s.get("sales_code") or "").upper() for s in sales}
                existing_names = {str(s.get("name") or "").lower() for s in sales}

                for u in users:
                    uname = u.get("username") or ""
                    disp_name = u.get("full_name") or uname
                    if uname.upper() not in existing_codes and disp_name.lower() not in existing_names:
                        sales.append({
                            "id": f"u_{u['id']}",
                            "sales_code": uname.upper()[:10],
                            "name": disp_name,
                            "email": u.get("email") or "",
                            "phone": "",
                            "commission_rate": 0.0,
                            "remarks": f"System User ({u.get('role', 'sales')})",
                            "is_active": True,
                        })
            except Exception:
                pass

            return sales


def get_salesperson(sales_id: Any, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if str(sales_id).startswith("u_"):
        uid = int(str(sales_id).split("_")[1])
        with get_connection() as conn:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, full_name, email FROM users WHERE id=%s", (uid,))
                u = cur.fetchone()
                if u:
                    ud = dict(u)
                    return {
                        "id": f"u_{ud['id']}",
                        "sales_code": ud["username"].upper()[:10],
                        "name": ud.get("full_name") or ud["username"],
                        "email": ud.get("email") or "",
                        "phone": "",
                        "commission_rate": 0.0,
                        "remarks": "System User",
                        "is_active": True,
                    }
                return None

    tenant = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, tenant_id, sales_code, name, email, phone, commission_rate, remarks, is_active
                FROM salespersons
                WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL OR tenant_id = 'default')
            """, (int(sales_id), tenant))
            row = cur.fetchone()
            return dict(row) if row else None


def save_salesperson(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> int:
    tenant = get_current_tenant_id()
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("Salesperson Name is required.")

    code = str(data.get("sales_code") or "").strip().upper()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            if not code:
                cur.execute("SELECT MAX(id) FROM salespersons WHERE tenant_id=%s OR tenant_id IS NULL OR tenant_id = 'default'", (tenant,))
                max_r = cur.fetchone()
                max_id = (max_r[0] if max_r and max_r[0] else 0) + 1
                code = f"SP{max_id:03d}"

            sid = data.get("id")
            # If editing a virtual user entry, create a real salespersons record
            if str(sid).startswith("u_"):
                sid = None

            email = str(data.get("email") or "").strip()
            phone = str(data.get("phone") or "").strip()
            comm = float(data.get("commission_rate") or 0.0)
            remarks = str(data.get("remarks") or "").strip()
            active = bool(data.get("is_active", True))

            if sid:
                cur.execute("""
                    UPDATE salespersons
                    SET sales_code = %s, name = %s, email = %s, phone = %s,
                        commission_rate = %s, remarks = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL OR tenant_id = 'default')
                """, (code, name, email, phone, comm, remarks, active, int(sid), tenant))
                conn.commit()
                return int(sid)
            else:
                # Check duplicate code
                cur.execute("""
                    SELECT id FROM salespersons
                    WHERE sales_code = %s AND (tenant_id = %s OR tenant_id IS NULL OR tenant_id = 'default')
                """, (code, tenant))
                dup = cur.fetchone()
                if dup:
                    dup_id = dup["id"] if isinstance(dup, dict) or hasattr(dup, "keys") else dup[0]
                    cur.execute("""
                        UPDATE salespersons
                        SET name = %s, email = %s, phone = %s, commission_rate = %s, remarks = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (name, email, phone, comm, remarks, active, dup_id))
                    conn.commit()
                    return dup_id

                cur.execute("""
                    INSERT INTO salespersons (tenant_id, sales_code, name, email, phone, commission_rate, remarks, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (tenant, code, name, email, phone, comm, remarks, active))
                conn.commit()
                cur.execute("SELECT id FROM salespersons WHERE sales_code = %s AND tenant_id = %s ORDER BY id DESC LIMIT 1", (code, tenant))
                row = cur.fetchone()
                return row["id"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]


def delete_salesperson(salesperson_id: Any, user: Optional[Dict[str, Any]] = None) -> bool:
    if str(salesperson_id).startswith("u_"):
        return True
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM salespersons
                WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL OR tenant_id = 'default')
            """, (int(salesperson_id), tenant))
            conn.commit()
            return True
