import os
import re

ignore = ['node_modules', 'venv', '__pycache__', '.git', 'frontend', 'ui', 'scratch']

tenant_vulns = []
rbac_checks = []
auth_issues = []
transaction_issues = []
financial_issues = []

for dp, dn, filenames in os.walk('.'):
    if any(i in dp for i in ignore):
        continue
    for f in filenames:
        if not f.endswith('.py'): continue
        filepath = os.path.join(dp, f)
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Tenant Isolation (WHERE id = %s without tenant_id)
                if re.search(r'WHERE\s+id\s*=\s*(%s|\?|\%s|\:\w+)', line, re.IGNORECASE):
                    if 'tenant_id' not in line:
                        # Quick check for multi-line queries
                        query_block = " ".join(lines[max(0, i-2):min(len(lines), i+3)])
                        if 'tenant_id' not in query_block.lower():
                            tenant_vulns.append(f"{filepath}:{i+1} -> {line.strip()}")
                
                # RBAC
                if 'st.session_state' in line and ('role' in line or 'permission' in line):
                    rbac_checks.append(f"{filepath}:{i+1} -> {line.strip()}")
                
                # Auth
                if 'password' in line.lower() or 'hash' in line.lower() or 'bcrypt' in line.lower():
                    auth_issues.append(f"{filepath}:{i+1} -> {line.strip()}")
                
                # Transactions
                if 'commit()' in line or 'rollback()' in line or 'Exception' in line:
                    if 'except' in line and 'rollback' not in content:
                        transaction_issues.append(f"{filepath} might swallow exceptions without rollback")
                
                # Financial
                if 'float(' in line and ('amount' in line.lower() or 'price' in line.lower() or 'total' in line.lower() or 'tax' in line.lower()):
                    financial_issues.append(f"{filepath}:{i+1} -> {line.strip()}")

with open('scratch/agent_security_audit.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT SECURITY & TENANT ISOLATION AUDIT\n\n")
    f.write("## Potential Tenant Leaks (Missing tenant_id in WHERE clause)\n")
    for v in set(tenant_vulns): f.write(f"- {v}\n")

with open('scratch/agent_rbac_audit.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT RBAC AUDIT\n\n")
    f.write("## RBAC checks found:\n")
    for v in set(rbac_checks): f.write(f"- {v}\n")

with open('scratch/agent_auth_audit.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT AUTH AUDIT\n\n")
    f.write("## Password/Hash related code:\n")
    for v in set(auth_issues): f.write(f"- {v}\n")

with open('scratch/agent_transaction_audit.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT TRANSACTION AUDIT\n\n")
    f.write("## Files with potential rollback/commit issues:\n")
    for v in set(transaction_issues): f.write(f"- {v}\n")

with open('scratch/agent_financial_audit.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT FINANCIAL AUDIT\n\n")
    f.write("## Risky float() conversions in financial contexts:\n")
    for v in set(financial_issues): f.write(f"- {v}\n")

print("Deep audit files generated.")
