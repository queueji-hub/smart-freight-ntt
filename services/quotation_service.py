from repositories.quotation_repo import create_quotation_db
from core.state import get

def create_quotation(form_data):

    state = get()

    data = {
        **form_data,
        "items": state["items"]
    }

    if not data["items"]:
        raise ValueError("Quotation must have at least 1 item")

    return create_quotation_db(data)