from datetime import date, datetime
from typing import Optional, Dict, List, Any
from database.connection import get_connection

SUPPORTED_CURRENCIES = ["THB", "USD", "EUR", "CNY", "JPY", "SGD", "HKD"]
BASE_CURRENCY = "THB"

def set_rate(currency: str, rate_to_thb: float,
             effective_date=None, source: str = "manual") -> int:
    """Set/update exchange rate using atomic returning."""
    eff = effective_date if isinstance(effective_date, date) else date.today()
    
    with get_connection() as conn:
        # ใช้ RETURNING id เพื่อความรวดเร็วและเป็น atomic
        cur = conn.execute("""
            INSERT INTO fx_rates (currency, rate_to_thb, effective_date, source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(currency, effective_date) DO UPDATE
            SET rate_to_thb = EXCLUDED.rate_to_thb,
                source = EXCLUDED.source
            RETURNING id
        """, (currency.upper(), float(rate_to_thb), eff, source))
        
        row = cur.fetchone()
        conn.commit()
        return row['id']

def get_rate(currency: str, on_date=None) -> float:
    """Get the most recent rate for a currency on or before given date."""
    if not currency or currency.upper() == BASE_CURRENCY:
        return 1.0
    
    on_date = on_date if isinstance(on_date, date) else date.today()
    
    with get_connection() as conn:
        row = conn.execute("""
            SELECT rate_to_thb FROM fx_rates
            WHERE currency=%s AND effective_date <= %s
            ORDER BY effective_date DESC LIMIT 1
        """, (currency.upper(), on_date)).fetchone()
        
    return float(row['rate_to_thb']) if row else 0.0

def convert(amount: float, from_cur: str, to_cur: str, on_date=None) -> float:
    """Convert amount between currencies via THB."""
    from_cur = (from_cur or BASE_CURRENCY).upper()
    to_cur = (to_cur or BASE_CURRENCY).upper()
    
    if from_cur == to_cur: return float(amount)
    
    rate_from = get_rate(from_cur, on_date)
    rate_to = get_rate(to_cur, on_date)
    
    if rate_from == 0 or rate_to == 0: return 0.0
    
    # Calculation: (Amount * From_Rate) / To_Rate
    return round((amount * rate_from) / rate_to, 2)

def list_rates(currency: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """List historical rates."""
    params = []
    sql = "SELECT * FROM fx_rates"
    if currency:
        sql += " WHERE currency=%s"
        params.append(currency.upper())
    sql += " ORDER BY effective_date DESC, id DESC LIMIT %s"
    params.append(limit)
    
    with get_connection() as conn:
        return list(conn.execute(sql, params).fetchall())

def latest_rates() -> Dict[str, float]:
    """Get the latest rate for each supported currency."""
    return {cur: get_rate(cur) for cur in SUPPORTED_CURRENCIES}


def calculate_fx_gain_loss(
    billed_amount_foreign: float,
    booking_fx_rate: float,
    settlement_fx_rate: float,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Calculates Realized FX Gain or Loss upon AR/AP settlement compared to invoice issuance rate.
    Formula: Realized Gain/Loss (THB) = Amount_Foreign * (Settlement_Rate - Billed_Rate)
    """
    if currency.upper() == BASE_CURRENCY:
        return {
            "billed_thb": round(billed_amount_foreign, 2),
            "settled_thb": round(billed_amount_foreign, 2),
            "fx_gain_loss_thb": 0.0,
            "status": "NEUTRAL"
        }

    billed_thb = billed_amount_foreign * booking_fx_rate
    settled_thb = billed_amount_foreign * settlement_fx_rate
    diff_thb = settled_thb - billed_thb

    return {
        "billed_thb": round(billed_thb, 2),
        "settled_thb": round(settled_thb, 2),
        "fx_gain_loss_thb": round(diff_thb, 2),
        "status": "GAIN" if diff_thb > 0 else ("LOSS" if diff_thb < 0 else "NEUTRAL")
    }