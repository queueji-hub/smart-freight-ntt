from managers.tenant_context import get_current_tenant_id
"""
Container Demurrage & Detention Free Time Guard Engine
Calculates Remaining Free Days & Overdue Penalty Exposure Risks
"""

from datetime import date, datetime
from typing import Dict, Any

def calculate_free_time_status(
    discharge_date: date,
    current_date: date = None,
    free_days: int = 7,
    demurrage_daily_rate_thb: float = 3500.0
) -> Dict[str, Any]:
    """
    Calculates remaining free time days and potential penalty charge exposure.
    Demurrage Starts = Discharge Date + Free Days
    """
    today = current_date or date.today()
    if isinstance(discharge_date, str):
        discharge_date = datetime.strptime(discharge_date[:10], "%Y-%m-%d").date()

    elapsed_days = (today - discharge_date).days
    remaining_free_days = free_days - elapsed_days

    if remaining_free_days >= 0:
        return {
            "status": "SAFE",
            "elapsed_days": elapsed_days,
            "remaining_free_days": remaining_free_days,
            "overdue_days": 0,
            "demurrage_penalty_thb": 0.0,
            "warning_message": f"SAFE: {remaining_free_days} free days remaining."
        }
    else:
        overdue_days = abs(remaining_free_days)
        penalty = overdue_days * demurrage_daily_rate_thb
        return {
            "status": "OVERDUE",
            "elapsed_days": elapsed_days,
            "remaining_free_days": 0,
            "overdue_days": overdue_days,
            "demurrage_penalty_thb": round(penalty, 2),
            "warning_message": f"🚨 DEMURRAGE OVERDUE: {overdue_days} days penalty exposure (฿{penalty:,.2f})."
        }
