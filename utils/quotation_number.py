from datetime import datetime

def _generate_quotation_no(job_type: str, quotation_date=None):
    dt = quotation_date or datetime.today().date()
    prefix = (job_type or "QTN")[:3].upper()

    return f"{prefix}-{dt.strftime('%Y%m%d')}-{int(datetime.now().timestamp())%10000}"