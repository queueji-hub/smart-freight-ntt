# AGENT SECURITY & TENANT ISOLATION AUDIT

## Potential Tenant Leaks (Missing tenant_id in WHERE clause)
- .\managers\profit_manager.py:84 -> cur.execute("DELETE FROM job_costs WHERE id=%s", (cost_id,))
- .\managers\customer_manager.py:214 -> WHERE id = %s
- .\managers\container_manager.py:252 -> sql = "DELETE FROM containers WHERE id=%s AND job_no=%s"
- .\managers\bl_manager.py:249 -> cur.execute("SELECT * FROM bills_of_lading WHERE id = %s", (bl_id,))
- .\managers\bl_manager.py:354 -> "UPDATE bills_of_lading SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
- .\managers\milestone_manager.py:57 -> DELETE FROM shipment_milestones WHERE id=%s AND job_no=%s
- .\managers\profit_manager.py:73 -> WHERE id=%s
- .\managers\bl_manager.py:395 -> cur.execute("SELECT job_no FROM containers WHERE id = %s", (container_id,))
- .\managers\bl_manager.py:320 -> cur.execute("DELETE FROM bills_of_lading WHERE id = %s", (bl_id,))
- .\managers\quotation_manager.py:223 -> WHERE id = %s;
- .\managers\invoice_manager.py:240 -> WHERE id = %s;
- .\managers\milestone_manager.py:41 -> UPDATE shipment_milestones SET event_date=%s, location=%s, remark=%s WHERE id=%s
- .\managers\profit_manager.py:153 -> cur.execute(f"UPDATE profit_sheets SET {col}_by=%s, {col}_at=CURRENT_TIMESTAMP WHERE id=%s",
- .\managers\profit_manager.py:60 -> cur.execute("SELECT amount, currency FROM job_costs WHERE id=%s", (cost_id,))
- .\repositories\quotation_repo.py:48 -> q = conn.execute("SELECT * FROM quotations WHERE id=%s", (qid,)).fetchone()
- .\managers\customer_manager.py:34 -> WHERE id = %s
- .\views\users_view.py:162 -> "UPDATE users SET role = %s WHERE id = %s",
- .\views\users_view.py:168 -> "UPDATE users SET role = ? WHERE id = ?",
- .\managers\bl_manager.py:304 -> f"UPDATE bills_of_lading SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id = %s",
