import re

def patch():
    path = "managers/dashboard_manager.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Inject tenant_id at the top of get_operational_control_tower_stats
    content = content.replace(
        "def get_operational_control_tower_stats() -> dict:",
        "def get_operational_control_tower_stats() -> dict:\n    from managers.tenant_context import get_current_tenant_id\n    tenant_id = get_current_tenant_id()"
    )
    
    # Replace FROM quotations with WHERE tenant_id
    content = content.replace("FROM quotations", "FROM quotations WHERE tenant_id = %s")
    content = content.replace('stats["quotation"] = {k: int(v or 0) for k, v in q_dict.items()}', 'stats["quotation"] = {k: int(v or 0) for k, v in q_dict.items()}')
    
    # To properly pass the parameter, we need to modify cur.execute calls
    # For quotations:
    content = re.sub(
        r'cur\.execute\(\"\"\"\s*SELECT\s*COUNT\(\*\) as total.*?FROM quotations WHERE tenant_id = %s\s*\"\"\"\)',
        r'cur.execute("""\n                    SELECT \n                        COUNT(*) as total,\n                        SUM(CASE WHEN LOWER(status) = \'draft\' THEN 1 ELSE 0 END) as draft,\n                        SUM(CASE WHEN LOWER(status) = \'active\' THEN 1 ELSE 0 END) as active,\n                        SUM(CASE WHEN LOWER(status) = \'converted\' THEN 1 ELSE 0 END) as converted,\n                        SUM(CASE WHEN LOWER(status) = \'expired\' THEN 1 ELSE 0 END) as expired\n                    FROM quotations WHERE tenant_id = %s\n                """, (tenant_id,))',
        content, flags=re.DOTALL
    )
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    patch()
