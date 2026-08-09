"""
System Audit Trail Logger Module
PostgreSQL Production Ready (SaaS & Multi-Tenant Architecture)
"""

from typing import Any, Optional
from datetime import datetime
from database.connection import get_connection

# =========================================================
# AUDIT CORE ENGINE (POSTGRESQL COMPLIANT)
# =========================================================
def log_action(
    user_id: int, 
    tenant_id: str, 
    entity: str, 
    entity_id: str, 
    action: str, 
    details: Optional[str] = None
) -> None:
    """
    Records security and operational changes into the central PostgreSQL log database.
    Designed with explicit cursor lifecycle management to ensure continuous availability.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO audit_logs (
                        user_id, 
                        tenant_id, 
                        entity, 
                        entity_id, 
                        action, 
                        details,
                        timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                """, (
                    user_id, 
                    tenant_id, 
                    entity, 
                    str(entity_id),  # Safely handle mixed integer or alphanumeric document numbers
                    action.upper().strip(), 
                    details
                ))
                
                # Permanently commit data change state
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                # Fail-safe operational fallback (Prevents business flow failure due to logging errors)
                import sys
                print(f"🚨 Audit Logger Intercept Failure: {str(sys.exc_info())}", file=sys.stderr)


def list_audit_logs(
    entity: Optional[str] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 200
) -> list:
    """
    Retrieves historical audit trail records matching optional entity, user_id, or search filters.
    """
    sql = """
        SELECT 
            a.id, a.user_id, a.tenant_id, a.entity, a.entity_id, a.action, a.details, a.timestamp,
            COALESCE(u.username, 'System') as username,
            COALESCE(u.full_name, 'System Operator') as full_name
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE 1=1
    """
    params = []

    if entity:
        sql += " AND LOWER(a.entity) = %s"
        params.append(entity.strip().lower())

    if user_id:
        sql += " AND a.user_id = %s"
        params.append(user_id)

    if search:
        sql += " AND (LOWER(a.entity_id) LIKE %s OR LOWER(a.action) LIKE %s OR LOWER(a.details) LIKE %s)"
        s_pattern = f"%{search.strip().lower()}%"
        params.extend([s_pattern, s_pattern, s_pattern])

    sql += " ORDER BY a.timestamp DESC, a.id DESC LIMIT %s"
    params.append(limit)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        print(f"[WARN] list_audit_logs query failed: {str(e)}")
        return []


# =========================================================
# BACKWARD COMPATIBILITY LINK (ALIAS MATRIX)
# =========================================================
def log(user_id: int, tenant_id: str, entity: str, entity_id: str, action: str) -> None:
    """
    Legacy method fallback alias mapping to new production ready log_action framework.
    Guarantees no disruption across un-migrated system components.
    """
    log_action(
        user_id=user_id,
        tenant_id=tenant_id,
        entity=entity,
        entity_id=entity_id,
        action=action
    )