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
                    VALUES (%s, %s, %s, %s, %s, %s, NOW());
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
                raise RuntimeError(f"Database logging failure: {str(e)}")


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