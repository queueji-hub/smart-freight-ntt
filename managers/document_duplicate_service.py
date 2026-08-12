"""Safe duplication and snapshot helpers for downstream documents.

Every duplicate is a NEW document with a fresh document number and DRAFT state.
Original records are never overwritten.
"""

from typing import Any, Dict, List, Tuple

from database.connection import get_connection
from managers.tenant_context import get_current_tenant_id


def _user_name(user: Dict[str, Any] | None) -> str:
    return str((user or {}).get("username") or "system")


def get_bl_snapshot(bl_id: int) -> Dict[str, Any]:
    """Read a B/L plus its manifest using explicit tenant-safe SQL."""
    from managers.bl_manager import list_bl_containers

    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bills_of_lading WHERE id=%s AND tenant_id=%s",
                (int(bl_id), tenant_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"B/L id={bl_id} not found.")
            bl = dict(row)
    return {
        "bl": bl,
        "job": {},
        "booking": {},
        "containers": list_bl_containers(int(bl_id)) or [],
    }


def duplicate_booking(booking_no: str, user: Dict[str, Any] | None = None) -> str:
    from managers.booking_manager import get_booking, create_booking

    source = get_booking(booking_no)
    if not source:
        raise ValueError(f"Booking '{booking_no}' not found.")
    if str(source.get("status", "DRAFT")).upper() in {"CANCELLED", "CONVERTED", "CONVERTED TO JOB"}:
        raise ValueError("Cancelled or converted bookings cannot be duplicated.")

    payload = dict(source)
    for key in (
        "id", "booking_no", "created_at", "updated_at", "job_no", "revision_no",
        "is_current", "previous_booking_id", "revision_reason", "revised_by", "revised_at",
    ):
        payload.pop(key, None)
    payload["status"] = "DRAFT"
    payload["created_by"] = _user_name(user)
    return create_booking(payload, user or {"username": _user_name(user), "id": 1})


def duplicate_bl(bl_id: int, user: Dict[str, Any] | None = None) -> int:
    from managers.bl_manager import create_bl, list_bl_containers, add_bl_container

    source_payload = get_bl_snapshot(int(bl_id))
    source = source_payload["bl"]
    if str(source.get("status", "Draft")).lower() == "cancelled":
        raise ValueError("Cancelled B/L documents cannot be duplicated.")
    job_no = source.get("job_no")
    bl_type = source.get("bl_type") or "HBL"
    if not job_no:
        raise ValueError("B/L has no linked Job and cannot be duplicated safely.")

    extra = dict(source)
    for key in ("id", "bl_no", "created_at", "updated_at", "status", "created_by"):
        extra.pop(key, None)
    extra["status"] = "Draft"
    extra["created_by"] = _user_name(user)

    new_id = create_bl(job_no, bl_type, user or {"username": _user_name(user)}, extra_data=extra)
    for container in list_bl_containers(int(bl_id)) or []:
        container_id = container.get("id")
        if container_id is not None:
            try:
                add_bl_container(new_id, container_id)
            except Exception:
                pass
    return new_id


def get_invoice_snapshot(doc_no: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    tenant_id = get_current_tenant_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM invoices WHERE doc_no=%s AND tenant_id=%s",
                (doc_no, tenant_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Financial document '{doc_no}' not found.")
            invoice = dict(row)
            cur.execute(
                """SELECT description, quantity, unit_price, amount, tax_type, wht_type
                   FROM invoice_items WHERE invoice_id=%s AND tenant_id=%s ORDER BY sort_order, id""",
                (invoice["id"], tenant_id),
            )
            items = [dict(r) for r in cur.fetchall()]
    return invoice, items


def duplicate_invoice(doc_no: str, user: Dict[str, Any] | None = None) -> str:
    from managers.invoice_manager import create_invoice

    invoice, items = get_invoice_snapshot(doc_no)
    if str(invoice.get("payment_status", "DRAFT")).upper() == "CANCELLED":
        raise ValueError("Cancelled financial documents cannot be duplicated.")

    payload = {
        "doc_type": invoice.get("doc_type", "INV"),
        "job_no": invoice.get("job_no"),
        "customer_id": invoice.get("customer_id"),
        "customer_name": invoice.get("customer_name"),
        "issue_date": invoice.get("issue_date"),
        "due_date": invoice.get("due_date"),
        "currency": invoice.get("currency", "THB"),
        "ref_doc_no": invoice.get("ref_doc_no"),
        "remark": invoice.get("remark"),
        "created_by": _user_name(user),
        "status": "DRAFT",
    }
    return create_invoice(payload, items)


def update_invoice_draft(doc_no: str, payload: Dict[str, Any], items: List[Dict[str, Any]]) -> bool:
    """Update only DRAFT financial documents, atomically replacing their lines."""
    from decimal import Decimal
    from managers.invoice_manager import calculate_summary

    tenant_id = get_current_tenant_id()
    summary = calculate_summary(items)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, payment_status FROM invoices WHERE doc_no=%s AND tenant_id=%s FOR UPDATE",
                (doc_no, tenant_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Financial document '{doc_no}' not found.")
            status = row[1] if isinstance(row, (tuple, list)) else row["payment_status"]
            invoice_id = row[0] if isinstance(row, (tuple, list)) else row["id"]
            if str(status).upper() != "DRAFT":
                raise ValueError("Only DRAFT financial documents can be edited.")

            cur.execute(
                """UPDATE invoices SET customer_id=%s, customer_name=%s, job_no=%s,
                   issue_date=%s, due_date=%s, currency=%s, ref_doc_no=%s, remark=%s,
                   subtotal=%s, vat_amount=%s, wht_amount=%s, total_amount=%s,
                   outstanding=%s WHERE id=%s AND tenant_id=%s""",
                (
                    payload.get("customer_id"), payload.get("customer_name"), payload.get("job_no"),
                    payload.get("issue_date"), payload.get("due_date"), payload.get("currency", "THB"),
                    payload.get("ref_doc_no"), payload.get("remark"),
                    summary["total_before_vat"], summary["total_vat_7"], summary["wht_total"],
                    summary["grand_total"], summary["grand_total"], invoice_id, tenant_id,
                ),
            )
            cur.execute("DELETE FROM invoice_items WHERE invoice_id=%s AND tenant_id=%s", (invoice_id, tenant_id))
            for idx, item in enumerate(items):
                qty = Decimal(str(item.get("quantity", 1)))
                price = Decimal(str(item.get("unit_price", 0)))
                cur.execute(
                    """INSERT INTO invoice_items
                       (invoice_id, description, quantity, unit_price, amount, tax_type, wht_type, sort_order, tenant_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        invoice_id, item.get("description", ""), qty, price, qty * price,
                        item.get("tax_type", "VAT 7%"), item.get("wht_type", "None"), idx, tenant_id,
                    ),
                )
            conn.commit()
    return True
