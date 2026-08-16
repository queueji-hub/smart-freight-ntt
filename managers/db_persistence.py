"""Database backup and persistence utilities."""
import base64
import hashlib
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from config import DB_PATH

_LAST_PUSH_AT = 0.0
_LAST_PUSH_HASH: Optional[str] = None


def _get_config() -> Optional[dict]:
    """Load GitHub configuration from Streamlit secrets safely."""
    try:
        import streamlit as st
        gh = st.secrets.get("github", {})
        if not gh:
            return None
        return {
            "token": gh.get("token", ""),
            "repo": gh.get("repo", ""),
            "branch": gh.get("branch", "main"),
            "db_path_in_repo": gh.get("db_path_in_repo", "data/smart_freight.db"),
            "author_name": gh.get("author_name", "FreightFlow NTT Bot"),
            "author_email": gh.get("author_email", "bot@nattayaraat.com"),
        }
    except Exception:
        return None


def _file_hash(path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    if not path.exists():
        return ""
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _gh_request(url: str, token: str, method: str = "GET", data: Optional[dict] = None) -> dict:
    """Perform GitHub API request safely with urllib."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SmartFreightNTT-Persistence",
    }
    payload_bytes = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=payload_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {"_status": resp.status}
    except urllib.error.HTTPError as exc:
        return {"_status": exc.code, "error": exc.reason}
    except Exception as exc:
        return {"_status": 500, "error": str(exc)}


def push_db_to_github(force: bool = False) -> Tuple[bool, str]:
    """Push local SQLite database backup to GitHub repository if configured."""
    global _LAST_PUSH_AT, _LAST_PUSH_HASH
    cfg = _get_config()

    db_file = Path(DB_PATH)
    if not cfg or not db_file.exists():
        return False, "GitHub persistence not configured or DB file missing"

    current_hash = _file_hash(db_file)
    if not force and current_hash == _LAST_PUSH_HASH:
        return False, "No changes detected since last sync"

    try:
        file_size = db_file.stat().st_size
        if file_size > 10 * 1024 * 1024:
            return False, f"Database file too large ({file_size / (1024*1024):.1f} MB exceeds 10 MB limit)"

        with open(db_file, "rb") as fh:
            content_b64 = base64.b64encode(fh.read()).decode("ascii")

        payload = {
            "message": f"Auto-backup DB: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64,
            "branch": cfg["branch"],
            "committer": {"name": cfg["author_name"], "email": cfg["author_email"]},
        }

        url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['db_path_in_repo']}"
        result = _gh_request(url, cfg["token"], "PUT", payload)

        if result.get("_status", 200) < 300:
            _LAST_PUSH_AT = time.time()
            _LAST_PUSH_HASH = current_hash
            return True, "Synced successfully"
        return False, f"GitHub sync error (status {result.get('_status')})"
    except Exception as exc:
        return False, str(exc)