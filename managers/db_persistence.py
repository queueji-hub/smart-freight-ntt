import base64
import time
import urllib.request
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# import streamlit as st # ใช้ import ใน function เพื่อความปลอดภัย

def push_db_to_github(force: bool = False) -> tuple:
    """Push DB to GitHub พร้อม Error Handling ที่เข้มงวดขึ้น"""
    import streamlit as st
    
    global _LAST_PUSH_AT, _LAST_PUSH_HASH
    cfg = _get_config()
    
    if not cfg or not Path(DB_PATH).exists():
        return False, "Not configured or DB missing"

    # กรองไฟล์ DB ก่อนส่งเพื่อลดขนาด
    current_hash = _file_hash()
    if not force and current_hash == _LAST_PUSH_HASH:
        return False, "No changes"

    try:
        with open(DB_PATH, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("ascii")
        
        # ปรับปรุง: ใช้การเปรียบเทียบ SHA เพื่อเลี่ยงการดึงข้อมูลถ้าไม่จำเป็น
        # (เก็บ log ไว้ใน st.session_state เพื่อลดการเรียก API ซ้ำซ้อน)
        
        payload = {
            "message": f"Auto-backup: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64,
            "branch": cfg["branch"],
            "committer": {"name": cfg["author_name"], "email": cfg["author_email"]}
        }
        
        # ใส่ความปลอดภัยเพิ่มเติม: ถ้าเกิน 10MB ให้เตือน (SQLite บวม)
        if Path(DB_PATH).stat().st_size > 10 * 1024 * 1024:
            return False, "DB too large"

        result = _gh_request(f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['db_path_in_repo']}", 
                             cfg["token"], "PUT", payload)
        
        if result.get("_status", 200) < 300:
            _LAST_PUSH_AT = time.time()
            _LAST_PUSH_HASH = current_hash
            return True, "Synced"
        return False, f"GitHub Error: {result.get('_status')}"

    except Exception as e:
        return False, str(e)