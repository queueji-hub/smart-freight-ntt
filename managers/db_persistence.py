"""Auto-persist SQLite DB to GitHub for Streamlit Cloud (which has ephemeral storage).

How it works:
1. On app boot: pull latest data/smart_freight.db from GitHub repo (if exists)
2. After each write operation: schedule a background commit+push to GitHub
3. Debounced — multiple writes within 30s become a single commit

Setup required (one-time):
1. Create a GitHub Personal Access Token (PAT) with 'repo' scope:
   https://github.com/settings/tokens
2. Add to Streamlit Cloud secrets (.streamlit/secrets.toml):
   [github]
   token = "ghp_xxx..."
   repo = "queueji-hub/smart-freight-ntt"
   branch = "main"
   author_name = "Smart Freight Bot"
   author_email = "bot@nattayaraat.com"
"""
import base64
import threading
import time
import urllib.request
import urllib.error
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import DB_PATH

try:
    import streamlit as st
except ImportError:
    st = None


# ===== Internals =====
_LOCK = threading.Lock()
_PENDING_TIMER: Optional[threading.Timer] = None
_DEBOUNCE_SECONDS = 30  # Wait this long after last write before pushing
_LAST_PUSH_AT = 0
_INITIAL_PULL_DONE = False


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
            "repo": cfg["repo"],  # e.g. "owner/repo"
            "branch": cfg.get("branch", "main"),
            "author_name": cfg.get("author_name", "Smart Freight Bot"),
            "author_email": cfg.get("author_email", "bot@nattayaraat.com"),
            "db_path_in_repo": cfg.get("db_path", "data/smart_freight.db"),
        }
    except Exception:
        return None


def _gh_request(url: str, token: str, method: str = "GET",
                data: dict = None) -> dict:
    """Make a GitHub API request."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "smart-freight-ntt")
    
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, data=body, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"_status": 404}
        raise
    except Exception:
        raise


def pull_db_from_github() -> bool:
    """Download the latest DB from GitHub repo on app startup.
    Returns True if pull succeeded, False if no remote DB or error."""
    global _INITIAL_PULL_DONE
    
    if _INITIAL_PULL_DONE:
        return True
    
    cfg = _get_config()
    if not cfg:
        _INITIAL_PULL_DONE = True
        return False
    
    try:
        url = (f"https://api.github.com/repos/{cfg['repo']}/contents/"
               f"{cfg['db_path_in_repo']}?ref={cfg['branch']}")
        result = _gh_request(url, cfg["token"])
        
        if result.get("_status") == 404:
            # No DB on GitHub yet — first run
            _INITIAL_PULL_DONE = True
            return False
        
        # Decode base64 content
        if "content" in result:
            content = base64.b64decode(result["content"])
            Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing local DB if any
            if Path(DB_PATH).exists():
                backup = Path(str(DB_PATH) + ".local-backup")
                try:
                    Path(DB_PATH).rename(backup)
                except Exception:
                    pass
            
            with open(DB_PATH, "wb") as f:
                f.write(content)
            
            _INITIAL_PULL_DONE = True
            return True
    except Exception:
        _INITIAL_PULL_DONE = True
        return False
    
    _INITIAL_PULL_DONE = True
    return False


def _push_db_now() -> bool:
    """Actually push DB to GitHub (synchronous). Called from timer thread."""
    global _LAST_PUSH_AT
    
    cfg = _get_config()
    if not cfg:
        return False
    
    if not Path(DB_PATH).exists():
        return False
    
    try:
        with _LOCK:
            # Read DB file
            with open(DB_PATH, "rb") as f:
                content_bytes = f.read()
            content_b64 = base64.b64encode(content_bytes).decode("ascii")
            
            # Get current SHA (needed for update)
            url = (f"https://api.github.com/repos/{cfg['repo']}/contents/"
                   f"{cfg['db_path_in_repo']}?ref={cfg['branch']}")
            existing = _gh_request(url, cfg["token"])
            sha = existing.get("sha") if existing.get("_status") != 404 else None
            
            # Commit
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
            
            _gh_request(commit_url, cfg["token"], "PUT", payload)
            _LAST_PUSH_AT = time.time()
            return True
    except Exception:
        return False


def schedule_push():
    """Debounced push — calls _push_db_now() after _DEBOUNCE_SECONDS of idle."""
    global _PENDING_TIMER
    
    cfg = _get_config()
    if not cfg:
        return  # No GitHub config — skip silently
    
    with _LOCK:
        if _PENDING_TIMER is not None:
            try:
                _PENDING_TIMER.cancel()
            except Exception:
                pass
        _PENDING_TIMER = threading.Timer(_DEBOUNCE_SECONDS, _push_db_now)
        _PENDING_TIMER.daemon = True
        _PENDING_TIMER.start()


def force_push() -> bool:
    """Manually trigger immediate push (for explicit save buttons)."""
    return _push_db_now()


def is_github_configured() -> bool:
    """Check if GitHub auto-backup is configured."""
    return _get_config() is not None


def get_backup_status() -> dict:
    """Return status info for display in UI."""
    cfg = _get_config()
    return {
        "configured": cfg is not None,
        "repo": cfg["repo"] if cfg else None,
        "last_push": _LAST_PUSH_AT,
        "last_push_str": (datetime.fromtimestamp(_LAST_PUSH_AT).strftime("%H:%M:%S")
                          if _LAST_PUSH_AT else "Never"),
        "initial_pull_done": _INITIAL_PULL_DONE,
    }
