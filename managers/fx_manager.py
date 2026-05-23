"""Foreign Exchange (FX) Rate management.

Stores exchange rates with effective dates so historical conversions remain
accurate. Default base currency is THB.
"""
from datetime import date, datetime
from typing import Optional, Dict, List, Any
from database.connection import get_connection

SUPPORTED_CURRENCIES = ["THB", "USD", "EUR", "CNY", "JPY", "SGD", "HKD"]
BASE_CURRENCY = "THB"

def _ensure_fx_table() -> None:
    """Create FX table if missing."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fx_rates (
                id SERIAL PRIMARY KEY,
                currency TEXT NOT NULL,
                rate_to_thb REAL NOT NULL,
                effective_date DATE NOT NULL,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(currency, effective_date)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fx_currency_date 
            ON fx_rates(currency, effective_date DESC)
        """)

def set_rate(currency: str, rate_to_thb: float,
             effective_date=None, source: str = "manual") -> int:
    """Set/update exchange rate. Returns row id."""
    _ensure_fx_table()
    eff = effective_date or date.today()
    if isinstance(eff, datetime):
        eff = eff.date()
    
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO fx_rates (currency, rate_to_thb, effective_date, source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(currency, effective_date) DO UPDATE
            SET rate_to_thb = EXCLUDED.rate_to_thb,
                source = EXCLUDED.source
        """, (currency.upper(), float(rate_to_thb), eff, source))
        
        cur = conn.execute(
            "SELECT id FROM fx_rates WHERE currency=%s AND effective_date=%s",
            (currency.upper(), eff)
        ).fetchone()
        
    # รองรับทั้ง row แบบ dict และ tuple
    return cur['id'] if isinstance(cur, dict) else cur[0]

def get_rate(currency: str, on_date=None) -> float:
    """Get the most recent rate for a currency on or before given date."""
    if not currency or currency.upper() == BASE_CURRENCY:
        return 1.0
    _ensure_fx_table()
    
    on_date = on_date or date.today()
    if isinstance(on_date, datetime):
        on_date = on_date.date()
    
    with get_connection() as conn:
        row = conn.execute("""
            SELECT rate_to_thb FROM fx_rates
            WHERE currency=%s AND effective_date <= %s
            ORDER BY effective_date DESC LIMIT 1
        """, (currency.upper(), on_date)).fetchone()
        
    if not row: return 0.0
    return float(row['rate_to_thb'] if isinstance(row, dict) else row[0])

def convert(amount: float, from_cur: str, to_cur: str, on_date=None) -> float:
    """Convert amount between currencies via THB."""
    from_cur = (from_cur or BASE_CURRENCY).upper()
    to_cur = (to_cur or BASE_CURRENCY).upper()
    if from_cur == to_cur:
        return float(amount)
    
    rate_from = get_rate(from_cur, on_date)
    rate_to = get_rate(to_cur, on_date)
    
    if rate_from == 0 or rate_to == 0:
        return 0.0
    
    # Convert through THB
    thb_amount = amount * rate_from
    if to_cur == BASE_CURRENCY:
        return round(thb_amount, 2)
    return round(thb_amount / rate_to, 2)

def list_rates(currency: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """List historical rates."""
    _ensure_fx_table()
    sql = "SELECT * FROM fx_rates"
    params = []
    if currency:
        sql += " WHERE currency=%s"
        params.append(currency.upper())
    sql += " ORDER BY effective_date DESC, id DESC LIMIT %s"
    params.append(limit)
    
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def latest_rates() -> Dict[str, float]:
    """Get the latest rate for each supported currency."""
    return {cur: get_rate(cur) for cur in SUPPORTED_CURRENCIES}

def seed_default_rates() -> None:
    """Seed sensible default rates if no rates exist."""
    _ensure_fx_table()
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM fx_rates").fetchone()
        count = row['cnt'] if isinstance(row, dict) else row[0]
        
    if count > 0: return
    
    defaults = {
        "USD": 35.50, "EUR": 38.00, "CNY": 4.95,
        "JPY": 0.235, "SGD": 26.40, "HKD": 4.55,
    }
    for cur, rate in defaults.items():
        set_rate(cur, rate, source="seed")