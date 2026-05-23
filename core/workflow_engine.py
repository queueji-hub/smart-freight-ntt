def transition(entity: str, current: str, action: str):

    rules = {
        "quotation": {
            "SEND": ("DRAFT", "SENT"),
            "ACCEPT": ("SENT", "ACCEPTED"),
            "CONVERT": ("ACCEPTED", "BOOKED"),
        },
        "booking": {
            "CONFIRM": ("PENDING", "CONFIRMED"),
            "TO_JOB": ("CONFIRMED", "JOB_CREATED"),
        },
        "job": {
            "START": ("OPEN", "IN_PROGRESS"),
            "SHIP": ("IN_PROGRESS", "IN_TRANSIT"),
            "CLOSE": ("IN_TRANSIT", "CLOSED"),
        }
    }

    if entity not in rules:
        raise Exception("Unknown entity")

    if action not in rules[entity]:
        raise Exception("Invalid action")

    from_state, to_state = rules[entity][action]

    if current != from_state:
        raise Exception(f"Invalid transition: {current}")

    return to_state