"""Database backup and persistence utilities."""
import base64
import hashlib
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config import DB_PATH

_LAST_PUSH_AT = 0.0
_LAST_PUSH_HASH: Optional[str] = None


def _get_config() -> Optional[dict]:
    """Load GitHub configuration from Streamlit secrets safely."""
    try:
        import streamlit as st
        if not hasattr(st, "secrets"):
            return None
        gh = st.secrets.get("github", {}) or st.secrets.get("persistence_engine", {})
        if not gh:
            return None
        token = gh.get("token", "") or gh.get("github_token", "")
        repo = gh.get("repo", "") or gh.get("repository_endpoint", "")
        if not token or not repo:
            return None
        return {
            "token": token,
            "repo": repo,
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

        url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['db_path_in_repo']}"
        existing = _gh_request(url, cfg["token"], "GET")
        
        payload = {
            "message": f"Auto-backup DB: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64,
            "branch": cfg["branch"],
            "committer": {"name": cfg["author_name"], "email": cfg["author_email"]},
        }
        if isinstance(existing, dict) and "sha" in existing:
            payload["sha"] = existing["sha"]

        result = _gh_request(url, cfg["token"], "PUT", payload)

        if result.get("_status", 200) < 300:
            _LAST_PUSH_AT = time.time()
            _LAST_PUSH_HASH = current_hash
            return True, "Synced successfully"
        return False, f"GitHub sync error (status {result.get('_status')})"
    except Exception as exc:
        return False, str(exc)


def force_push() -> Tuple[bool, str]:
    """Force push local database snapshot to GitHub repository."""
    return push_db_to_github(force=True)


def get_backup_status() -> Dict[str, Any]:
    """Return status dictionary of database backup and GitHub persistence."""
    global _LAST_PUSH_AT, _LAST_PUSH_HASH
    cfg = _get_config()
    db_file = Path(DB_PATH)
    db_exists = db_file.exists()
    db_size = db_file.stat().st_size if db_exists else 0
    current_hash = _file_hash(db_file) if db_exists else ""
    is_dirty = (current_hash != _LAST_PUSH_HASH) if (_LAST_PUSH_HASH and current_hash) else True
    last_push_str = datetime.fromtimestamp(_LAST_PUSH_AT).strftime("%Y-%m-%d %H:%M:%S") if _LAST_PUSH_AT > 0 else "Never"

    return {
        "configured": bool(cfg and db_exists),
        "last_push_str": last_push_str,
        "db_size_bytes": db_size,
        "is_dirty": is_dirty,
        "repo": cfg.get("repo") if cfg else None,
        "branch": cfg.get("branch") if cfg else None,
    }