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
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            param_placeholder = "?" if is_sqlite else "%s"
            
            try:
                sql = f"""
                    SELECT id, tenant_id, sales_code, name, email, phone, commission_rate, remarks, is_active, created_at, updated_at
                    FROM salespersons
                    WHERE (tenant_id = {param_placeholder} OR tenant_id IS NULL OR tenant_id = 'default')
                """
                if active_only:
                    sql += " AND (is_active = 1 OR is_active = '1' OR is_active IS NULL)" if is_sqlite else " AND (is_active = TRUE OR is_active = 1)"
                sql += " ORDER BY sales_code ASC, name ASC"
                cur.execute(sql, (tenant,))
                sales = [dict(r) for r in cur.fetchall()]
            except Exception:
                pass

            # Also include users from users table by ensuring/syncing them as real salespersons
            try:
                cur.execute("""
                    SELECT id, username, full_name, email, role
                    FROM users
                    ORDER BY id ASC
                """)
                users = [dict(r) for r in cur.fetchall()]
                existing_codes = {str(s.get("sales_code") or "").upper() for s in sales}
                existing_names = {str(s.get("name") or "").lower() for s in sales}

                for u in users:
                    uname = u.get("username") or ""
                    disp_name = u.get("full_name") or uname
                    urole = str(u.get("role") or "").lower()
                    if urole in ("sales", "admin", "manager", "operation") or len(sales) == 0:
                        if uname.upper() not in existing_codes and disp_name.lower() not in existing_names:
                            # Auto-create genuine record in salespersons table
                            scode = uname.upper()[:10]
                            cur.execute(f"""
                                INSERT INTO salespersons (tenant_id, sales_code, name, email, remarks, is_active)
                                VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})
                            """ if is_sqlite else f"""
                                INSERT INTO salespersons (tenant_id, sales_code, name, email, remarks, is_active)
                                VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})
                                RETURNING id
                            """, (tenant, scode, disp_name, u.get("email") or "", f"System User ({urole})", 1 if is_sqlite else True))
                            if is_sqlite:
                                new_id = cur.lastrowid
                            else:
                                ret_row = cur.fetchone()
                                new_id = ret_row[0] if ret_row else u["id"]
                            conn.commit()

                            sales.append({
                                "id": new_id,
                                "sales_code": scode,
                                "name": disp_name,
                                "email": u.get("email") or "",
                                "phone": "",
                                "commission_rate": 0.0,
                                "remarks": f"System User ({urole})",
                                "is_active": True,
                            })
                            existing_codes.add(scode)
                            existing_names.add(disp_name.lower())
            except Exception:
                pass

            if not sales:
                sales = [
                    {
                        "id": 1,
                        "sales_code": "SP001",
                        "name": "Spicy (Managing Director / Sales)",
                        "email": "management@nattayaraat.com",
                        "phone": "063-428-9691",
                        "commission_rate": 0.0,
                        "remarks": "Default Sales Representative",
                        "is_active": True,
                    }
                ]

            return sales


def resolve_salesperson_id(sales_id: Any, tenant: str = "default") -> Optional[int]:
    if not sales_id:
        return None
    if isinstance(sales_id, int):
        return sales_id
    sid_str = str(sales_id).strip()
    if sid_str.isdigit():
        return int(sid_str)
    if sid_str.startswith("u_"):
        uid_str = sid_str.split("_")[1]
        if uid_str.isdigit():
            uid = int(uid_str)
            with get_connection() as conn:
                _ensure_schema(conn)
                with conn.cursor() as cur:
                    is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
                    p = "?" if is_sqlite else "%s"
                    cur.execute(f"SELECT id, username, full_name, email FROM users WHERE id={p}", (uid,))
                    u = cur.fetchone()
                    if u:
                        uname = u.get("username") or f"USER{uid}"
                        disp_name = u.get("full_name") or uname
                        cur.execute(f"SELECT id FROM salespersons WHERE sales_code={p} AND (tenant_id={p} OR tenant_id IS NULL OR tenant_id='default')", (uname.upper()[:20], tenant))
                        sp = cur.fetchone()
                        if sp:
                            return sp["id"] if isinstance(sp, dict) or hasattr(sp, "keys") else sp[0]
                        else:
                            cur.execute(f"""
                                INSERT INTO salespersons (tenant_id, sales_code, name, email, remarks, is_active)
                                VALUES ({p}, {p}, {p}, {p}, 'Auto-created from User', 1)
                            """ if is_sqlite else f"""
                                INSERT INTO salespersons (tenant_id, sales_code, name, email, remarks, is_active)
                                VALUES ({p}, {p}, {p}, {p}, 'Auto-created from User', TRUE)
                                RETURNING id
                            """, (tenant, uname.upper()[:20], disp_name, u.get("email") or ""))
                            if is_sqlite:
                                return cur.lastrowid
                            else:
                                ret_row = cur.fetchone()
                                conn.commit()
                                return ret_row[0] if ret_row else uid
            return uid
    return None


def get_salesperson(sales_id: Any, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    real_id = resolve_salesperson_id(sales_id)
    if not real_id:
        return None
    tenant = get_current_tenant_id()
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, tenant_id, sales_code, name, email, phone, commission_rate, remarks, is_active
                FROM salespersons
                WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL OR tenant_id = 'default')
            """, (int(real_id), tenant))
            row = cur.fetchone()
            return dict(row) if row else None


def _scalar(row: Any) -> Any:
    if not row:
        return None
    if isinstance(row, dict) or hasattr(row, "values"):
        vals = list(row.values())
        return vals[0] if vals else None
    if isinstance(row, (list, tuple)):
        return row[0]
    return row


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
                max_v = _scalar(cur.fetchone())
                max_id = (int(max_v) if max_v is not None else 0) + 1
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
    if not salesperson_id:
        return False
    tenant = get_current_tenant_id()
    sid_str = str(salesperson_id).strip()
    
    with get_connection() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            is_sqlite = type(conn).__name__ == "SQLiteConnAdapter" or "sqlite" in str(type(conn)).lower()
            param_placeholder = "?" if is_sqlite else "%s"

            if sid_str.startswith("u_"):
                uid = sid_str.split("_")[1]
                cur.execute(f"SELECT id, username, full_name, email FROM users WHERE id={param_placeholder}", (uid,))
                u = cur.fetchone()
                if u:
                    uname = u.get("username") or ""
                    disp_name = u.get("full_name") or uname
                    # Insert inactive record into salespersons so it's ignored and excluded from list
                    cur.execute(f"""
                        INSERT INTO salespersons (tenant_id, sales_code, name, email, remarks, is_active)
                        VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, 'Excluded from Sales', 0)
                    """ if is_sqlite else f"""
                        INSERT INTO salespersons (tenant_id, sales_code, name, email, remarks, is_active)
                        VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, 'Excluded from Sales', FALSE)
                    """, (tenant, uname.upper()[:10], disp_name, u.get("email") or ""))
            else:
                try:
                    cur.execute(f"""
                        DELETE FROM salespersons
                        WHERE id = {param_placeholder} AND (tenant_id = {param_placeholder} OR tenant_id IS NULL OR tenant_id = 'default')
                    """, (int(salesperson_id), tenant))
                except Exception:
                    cur.execute(f"""
                        UPDATE salespersons SET is_active = 0
                        WHERE id = {param_placeholder} AND (tenant_id = {param_placeholder} OR tenant_id IS NULL OR tenant_id = 'default')
                    """ if is_sqlite else f"""
                        UPDATE salespersons SET is_active = FALSE
                        WHERE id = {param_placeholder} AND (tenant_id = {param_placeholder} OR tenant_id IS NULL OR tenant_id = 'default')
                    """, (int(salesperson_id), tenant))
            conn.commit()
            return True
