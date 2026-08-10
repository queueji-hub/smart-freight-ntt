import os
import ast
import json

ignore = ['node_modules', 'venv', '__pycache__', '.git', 'freight-os-compact', 'freight-os-mvp', 'frontend', 'ui', 'temp', 'output', 'logs']

file_inventory = []
imports_map = {}
sql_queries = {}

for dp, dn, filenames in os.walk('.'):
    if any(i in dp for i in ignore):
        continue
    for f in filenames:
        if f.endswith('.py'):
            filepath = os.path.join(dp, f)
            file_inventory.append(filepath)
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                
            try:
                tree = ast.parse(content)
                imports = []
                sqls = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                    elif isinstance(node, ast.Str):
                        val = node.s.strip().upper()
                        if val.startswith("SELECT ") or val.startswith("INSERT ") or val.startswith("UPDATE ") or val.startswith("DELETE ") or val.startswith("CREATE "):
                            sqls.append(node.s.strip())
                imports_map[filepath] = imports
                if sqls:
                    sql_queries[filepath] = sqls
            except Exception as e:
                pass

with open('scratch/agent_repository_inventory.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT REPOSITORY INVENTORY\n\n")
    for file in sorted(file_inventory):
        f.write(f"- `{file}`\n")

with open('scratch/agent_architecture_audit.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT ARCHITECTURE AUDIT\n\n")
    f.write("## Dependencies Map\n")
    for file, imp in imports_map.items():
        if imp:
            f.write(f"### {file}\n")
            for i in set(imp):
                if 'managers' in i or 'database' in i or 'views' in i or 'pdf' in i:
                    f.write(f"- {i}\n")

with open('scratch/agent_database_audit.md', 'w', encoding='utf-8') as f:
    f.write("# AGENT DATABASE AUDIT (Raw SQL extraction)\n\n")
    for file, sqls in sql_queries.items():
        f.write(f"### {file}\n")
        for s in set(sqls):
            f.write(f"```sql\n{s}\n```\n")

print("Files generated.")
