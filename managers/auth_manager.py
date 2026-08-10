"""
Authentication & Enterprise Role-Based Access Control (RBAC) Subsystem
Secure Cryptographic Hashing & SQL Data Access Handlers — 100% Professional ERP Grade
"""

import bcrypt
from typing import Optional, Dict, Any, List
from database.connection import get_connection

# =========================================================
# ROLE PERMISSIONS CONTROL MATRIX
# =========================================================
PERMISSIONS = {
    "admin": {
        "dashboard": "rw", "crm": "rw", "quotation": "rw", "booking": "rw",
        "shipment": "rw", "bl": "rw", "tracking": "rw", "profit": "rw", "billing": "rw",
        "fx": "rw", "reports": "rw", "users": "rw", "settings": "rw",
    },
    "sales": {
        "dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "r",
        "shipment": "r", "bl": "r", "tracking": "r", "billing": "r", "reports": "r",
    },
    "operation": {
        "dashboard": "r", "crm": "rw", "quotation": "rw", "booking": "rw",
        "shipment": "rw", "bl": "rw", "tracking": "rw", "billing": "r", "reports": "r",
    },
    "accounting": {
        "dashboard": "r", "crm": "r", "quotation": "r", "booking": "r",
        "shipment": "r", "bl": "r", "billing": "rw", "reports": "rw",
    },
}

ROLE_LABELS = {
    "admin": "Administrator",
    "sales": "Sales Professional",
    "operation": "Logistics Operation",
    "accounting": "Financial Accounting",
}

# =========================================================
# COMPLIANCE USER CONTRACT NORMALIZATION
# =========================================================
def normalize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures consistent user payload schema boundaries across view states."""
    return {
        "id": user.get("id"),
        "username": str(user.get("username", "")).strip().lower(),
        "full_name": user.get("full_name") or user.get("username", "System User"),
        "email": str(user.get("email", "")).strip(),
        "role": str(user.get("role", "sales")).strip().lower(),
        "is_active": int(user.get("is_active", 1)),
    }

# =========================================================
# ARBITRARY PERMISSION HELPERS
# =========================================================
def can(role: str, module: str, action: str = "r") -> bool:
    """Evaluates strict access authorization clearance across the RBAC profile matrix."""
    if not role:
        return False
        
    perms = PERMISSIONS.get(str(role).strip().lower(), {})
    granted = perms.get(str(module).strip().lower(), "")
    
    if action == "r":
        return "r" in granted or "w" in granted
    if action == "w":
        return "w" in granted
        
    return False

def can_read(role: str, module: str) -> bool:
    return can(role, module, "r")

def can_write(role: str, module: str) -> bool:
    return can(role, module, "w")

# =========================================================
# CRYPTOGRAPHIC CRYPTO PASSWORD HELPERS
# =========================================================
def hash_password(password: str) -> str:
    """Generates secure cryptographic password hashes using blowfish cipher keys."""
    password_str = (password or "").strip()
    return bcrypt.hashpw(
        password_str.encode("utf-8"),
        bcrypt.gensalt(rounds=12) # Standard production security cost parameter
    ).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Verifies clear text passwords against their encrypted storage tokens."""
    try:
        if not password or not hashed:
            return False
            
        password_bytes = password.strip().encode("utf-8")
        hashed_bytes = hashed.strip().encode("utf-8")
        
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as crypto_err:
        print(f"🚨 SECURITY LAYER ERROR: Cryptographic verification fault intercepted: {str(crypto_err)}")
        return False

# =========================================================
# CENTRAL IDENTITY AUTHENTICATION ENGINE
# =========================================================
def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates user account data parameters against master ledger directory files."""
    try:
        clean_username = (username or "").strip().lower()
        clean_password = (password or "").strip()
        
        if not clean_username or not clean_password:
            return None
            
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, username, password_hash, full_name, email, role, is_active 
                    FROM users 
                    WHERE LOWER(username) = %s 
                    LIMIT 1
                    """,
                    (clean_username,)
                )
                
                row = cur.fetchone()
                if not row:
                    print(f"🔒 AUTH WARNING: Sign-in attempt rejected. User record context not found: '{clean_username}'")
                    return None
                
                # Safe Map Data Parameters to Dictionary Profile Object
                # วิธีนี้ช่วยป้องกันบั๊กกรณี Cursor โหมด Real-Row Mapping คืนค่ากลับมาเป็น Tuple
                user_data = {}
                if hasattr(row, "keys"):
                    user_data = dict(row)
                else:
                    # Fallback mapping schema sequence arrays based on explicit query positioning
                    cols = ["id", "username", "password_hash", "full_name", "email", "role", "is_active"]
                    user_data = dict(zip(cols, row))
                    
                stored_hash = user_data.get("password_hash")
                if not stored_hash:
                    print("🔒 AUTH CRITICAL: Blocked authentication sequence. Target identity missing password hashes tokens.")
                    return None
                    
                if not verify_password(clean_password, stored_hash):
                    print(f"🔒 AUTH WARNING: Validation check failed for credential identifiers: '{clean_username}'")
                    return None
                    
                if int(user_data.get("is_active", 1)) != 1:
                    print(f"🔒 AUTH REJECTED: User account identity is currently administratively disabled: '{clean_username}'")
                    return None
                    
                user_data.pop("password_hash", None)
                return normalize_user(user_data)
                
    except Exception as pipeline_fault:
        print(f"🚨 IDENTITY CRITICAL EXCEPTION: Authentication service pipeline crash: {str(pipeline_fault)}")
        return None

# =========================================================
# DATA FETCHING LAYER QUERIES
# =========================================================
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Queries and filters target system identities records by username reference."""
    try:
        clean_username = (username or "").strip().lower()
        if not clean_username:
            return None
            
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, full_name, email, role, is_active FROM users WHERE LOWER(username) = %s LIMIT 1",
                    (clean_username,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                    
                if hasattr(row, "keys"):
                    user_data = dict(row)
                else:
                    cols = ["id", "username", "full_name", "email", "role", "is_active"]
                    user_data = dict(zip(cols, row))
                    
                user_data.pop("password_hash", None)
                return normalize_user(user_data)
    except Exception as fetch_ex:
        print(f"🚨 DATA RETRIEVAL EXCEPTION: Failed user profile fetch execution: {str(fetch_ex)}")
        return None

def list_users() -> List[Dict[str, Any]]:
    """Compiles list array of all corporate active profile records schemas cataloged inside the cluster."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, full_name, email, role, is_active FROM users ORDER BY username ASC")
                rows = cur.fetchall()
                
                results = []
                cols = ["id", "username", "full_name", "email", "role", "is_active"]
                
                for r in rows:
                    r_dict = dict(r) if hasattr(r, "keys") else dict(zip(cols, r))
                    results.append(normalize_user(r_dict))
                return results
    except Exception as list_ex:
        print(f"🚨 DATA RETRIEVAL EXCEPTION: Failed compilation log rows: {str(list_ex)}")
        return []

# =========================================================
# MUTATION AND DATA WRITE ACTIONS
# =========================================================
def create_user(username: str, password: str, full_name: str = "", email: str = "", role: str = "sales") -> None:
    """Injects and provisions a new secure multi-currency tenant operator credential block."""
    clean_username = (username or "").strip().lower()
    if not clean_username:
        raise ValueError("System validation constraint fault: Username parameter mandatory row configuration.")
        
    if get_user_by_username(clean_username):
        raise ValueError(f"Operational constraint error: Identity token '{clean_username}' already allocated within network rows.")
        
    password_hash = hash_password(password)
    clean_role = str(role).strip().lower()
    if clean_role not in PERMISSIONS:
        clean_role = "sales" # Safeguard assignment allocation onto minimum clearance scope
        
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, email, role, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (clean_username, password_hash, full_name.strip(), email.strip(), clean_role, 1)
                )
                conn.commit()
        print(f"✅ SECURITY SYSTEM PROVISIONING: New identity account created: '{clean_username}' [{clean_role}]")
    except Exception as insert_fault:
        print(f"🚨 MUTATION TRANSACTION CRASH: Failed to commit new system workspace record profile: {str(insert_fault)}")
        raise insert_fault

def update_user_password(username: str, new_password: str) -> None:
    """Intercepts and updates system records password keys using salted blowfish encryptions."""
    clean_username = (username or "").strip().lower()
    password_hash = hash_password(new_password)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE LOWER(username) = %s",
                    (password_hash, clean_username)
                )
                conn.commit()
                if cur.rowcount == 0:
                    raise KeyError(f"Identity context sequence identifier token not found: '{clean_username}'")
        print(f"✅ SECURITY RECORD MUTATION: Password cipher data successfully changed: '{clean_username}'")
    except Exception as update_fault:
        print(f"🚨 SECURITY LAYER FAULT: Password mutation sequence blocked structural record update: {str(update_fault)}")
        raise update_fault

def update_user_role(username: str, role: str) -> None:
    """Mutates operational verification clearance profiles assigned onto users."""
    clean_username = (username or "").strip().lower()
    clean_role = str(role).strip().lower()
    
    if clean_role not in PERMISSIONS:
        raise ValueError(f"System scope authorization error: Selected operational parameters role class invalid: '{clean_role}'")
        
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET role = %s WHERE LOWER(username) = %s",
                    (clean_role, clean_username)
                )
                conn.commit()
        print(f"✅ SECURITY ACCESS LOG CHANGE: Modified role clear spectrum for account identity '{clean_username}' to [{clean_role}]")
    except Exception as role_mut_fault:
        print(f"🚨 ACCESS POLICY OVERWRITE FAULT: Authorization matrix write sequence failure: {str(role_mut_fault)}")
        raise role_mut_fault

def set_user_active(username: str, active: bool) -> None:
    """Administratively activates or locks specific account profiles from access clear corridors."""
    clean_username = (username or "").strip().lower()
    status_bit = 1 if active else 0
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET is_active = %s WHERE LOWER(username) = %s",
                    (status_bit, clean_username)
                )
                conn.commit()
        print(f"✅ SYSTEM AUDIT MODIFIER: System login availability updated for credential index '{clean_username}' -> State: [Active={active}]")
    except Exception as active_mut_fault:
        print(f"🚨 IDENTITY CONTEXT OVERWRITE ERROR: Failure updating user active flag variables: {str(active_mut_fault)}")
        raise active_mut_fault