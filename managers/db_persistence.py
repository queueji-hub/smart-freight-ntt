"""Auto-persist SQLite DB to GitHub for Streamlit Cloud (ephemeral storage).

Strategy:
1. On app boot: pull latest data/smart_freight.db from GitHub repo
2. After each write: schedule a synchronous push (debounced 5 sec via session_state)
3. No background threads — Streamlit Cloud kills threads on sleep

Setup required (one-time):
1. Create a GitHub Personal Access Token (PAT) with 'repo' scope:
   https://github.com/settings/tokens
2. Add to Streamlit Cloud secrets:
   [github]
   token = "ghp_xxx..."
   repo = "queueji-hub/smart-freight-ntt"
   branch = "main"
   author_name = "Smart Freight Bot"
   author_email = "bot@nattayaraat.com"
   db_path = "data/smart_freight.db"
"""
import base64
import time
import urllib.request
import urllib.error
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import DB_PATH

try:
    import streamlit as st
except ImportError:
    st = None


_LAST_PUSH_AT = 0
_LAST_PUSH_HASH = None  # SHA256 of last pushed DB content
_INITIAL_PULL_DONE = False
_MIN_PUSH_INTERVAL = 5  # seconds — avoid push storms


def _get_config() -> Optional[dict]:
    """Read GitHub config from Streamlit secrets."""
    if st is None:
        return None
    try:
        cfg = dict(st.secrets["github"])
        if not cfg.get("token") or not cfg.get("repo"):
            return None
        return {
            "token": cfg["token"],
            "repo": cfg["repo"],
            "branch": cfg.get("branch", "main"),
            "author_name": cfg.get("author_name", "Smart Freight Bot"),
            "author_email": cfg.get("author_email", "bot@nattayaraat.com"),
            "db_path_in_repo": cfg.get("db_path", "data/smart_freight.db"),
        }
    except Exception:
        return None


def _gh_request(url: str, token: str, method: str = "GET",
                data: dict = None, timeout: int = 20) -> dict:
    """Make a GitHub API request. Returns dict with _status on errors."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "smart-freight-ntt")
    
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, data=body, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        return {"_status": e.code, "_error": err_body}
    except Exception as e:
        return {"_status": -1, "_error": str(e)}


def pull_db_from_github(force: bool = False) -> tuple:
    """Download the latest DB from GitHub repo on app startup.
    Returns (success: bool, message: str)."""
    global _INITIAL_PULL_DONE
    
    if _INITIAL_PULL_DONE and not force:
        return True, "already pulled"
    
    cfg = _get_config()
    if not cfg:
        _INITIAL_PULL_DONE = True
        return False, "GitHub not configured"
    
    url = (f"https://api.github.com/repos/{cfg['repo']}/contents/"
           f"{cfg['db_path_in_repo']}?ref={cfg['branch']}")
    result = _gh_request(url, cfg["token"])
    
    if result.get("_status") == 404:
        _INITIAL_PULL_DONE = True
        return False, "No DB on GitHub yet (first run)"
    
    if result.get("_status") and result["_status"] >= 400:
        _INITIAL_PULL_DONE = True
        return False, f"GitHub error: {result.get('_status')} {result.get('_error','')[:100]}"
    
    if "content" not in result:
        _INITIAL_PULL_DONE = True
        return False, "Invalid response from GitHub"
    
    try:
        content = base64.b64decode(result["content"])
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        # Write the DB file
        with open(DB_PATH, "wb") as f:
            f.write(content)
        
        _INITIAL_PULL_DONE = True
        return True, f"Pulled {len(content)} bytes from {cfg['repo']}"
    except Exception as e:
        _INITIAL_PULL_DONE = True
        return False, f"Write failed: {e}"


def _file_hash() -> Optional[str]:
    """Compute SHA256 of current DB file."""
    if not Path(DB_PATH).exists():
        return None
    try:
        with open(DB_PATH, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def push_db_to_github(force: bool = False) -> tuple:
    """Push DB to GitHub (synchronous). Returns (success: bool, message: str).
    
    Skips if:
    - GitHub not configured
    - DB file doesn't exist
    - Pushed within _MIN_PUSH_INTERVAL seconds (unless force=True)
    - DB content unchanged since last push (unless force=True)
    """
    global _LAST_PUSH_AT, _LAST_PUSH_HASH
    
    cfg = _get_config()
    if not cfg:
        return False, "GitHub not configured"
    
    if not Path(DB_PATH).exists():
        return False, "DB file not found"
    
    # Rate limit
    now = time.time()
    if not force and (now - _LAST_PUSH_AT) < _MIN_PUSH_INTERVAL:
        return False, f"Too soon (wait {_MIN_PUSH_INTERVAL}s)"
    
    # Skip if content unchanged
    current_hash = _file_hash()
    if not force and current_hash == _LAST_PUSH_HASH:
        return False, "No changes since last push"
    
    try:
        with open(DB_PATH, "rb") as f:
            content_bytes = f.read()
        content_b64 = base64.b64encode(content_bytes).decode("ascii")
        
        # Get current SHA from GitHub
        url = (f"https://api.github.com/repos/{cfg['repo']}/contents/"
               f"{cfg['db_path_in_repo']}?ref={cfg['branch']}")
        existing = _gh_request(url, cfg["token"])
        sha = existing.get("sha") if existing.get("_status") != 404 else None
        
        # Push commit
        commit_url = (f"https://api.github.com/repos/{cfg['repo']}/contents/"
                       f"{cfg['db_path_in_repo']}")
        payload = {
            "message": (f"Auto-backup DB at "
                         f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
            "content": content_b64,
            "branch": cfg["branch"],
            "committer": {
                "name": cfg["author_name"],
                "email": cfg["author_email"],
            },
        }
        if sha:
            payload["sha"] = sha
        
        result = _gh_request(commit_url, cfg["token"], "PUT", payload)
        
        if result.get("_status") and result["_status"] >= 400:
            return False, f"Push failed: {result.get('_status')} {result.get('_error','')[:200]}"
        
        _LAST_PUSH_AT = now
        _LAST_PUSH_HASH = current_hash
        return True, f"Pushed {len(content_bytes)} bytes"
    
    except Exception as e:
        return False, f"Push error: {e}"


def schedule_push():
    """Mark DB as dirty in session_state. The actual push happens on:
    - Explicit save button
    - Page navigation (via Dashboard.py session check)
    - User action that calls force_push()
    
    NOTE: Streamlit Cloud does not allow background threads reliably,
    so we don't use threading.Timer anymore.
    """
    if st is None:
        return
    try:
        st.session_state["_db_dirty"] = True
        st.session_state["_db_dirty_at"] = time.time()
    except Exception:
        pass


def push_if_dirty() -> tuple:
    """Push DB to GitHub if marked dirty. Called from Dashboard.py on each rerun.
    Pushes only if _MIN_PUSH_INTERVAL seconds have passed since last write."""
    if st is None:
        return False, "No streamlit"
    
    if not st.session_state.get("_db_dirty"):
        return False, "Not dirty"
    
    dirty_at = st.session_state.get("_db_dirty_at", 0)
    now = time.time()
    
    # Wait at least 3 seconds after the last write to batch multiple ops
    if (now - dirty_at) < 3:
        return False, "Waiting for batch"
    
    ok, msg = push_db_to_github()
    if ok:
        st.session_state["_db_dirty"] = False
    return ok, msg


def force_push() -> tuple:
    """Push immediately (skips rate limit and dirty check)."""
    if st is not None:
        st.session_state["_db_dirty"] = False
    return push_db_to_github(force=True)


def is_github_configured() -> bool:
    return _get_config() is not None


def get_backup_status() -> dict:
    """Return status info for UI display."""
    cfg = _get_config()
    return {
        "configured": cfg is not None,
        "repo": cfg["repo"] if cfg else None,
        "branch": cfg["branch"] if cfg else None,
        "last_push": _LAST_PUSH_AT,
        "last_push_str": (datetime.fromtimestamp(_LAST_PUSH_AT).strftime("%H:%M:%S")
                          if _LAST_PUSH_AT else "Never"),
        "initial_pull_done": _INITIAL_PULL_DONE,
        "db_exists": Path(DB_PATH).exists(),
        "db_size_bytes": (Path(DB_PATH).stat().st_size
                          if Path(DB_PATH).exists() else 0),
        "is_dirty": st.session_state.get("_db_dirty", False) if st else False,
    }
