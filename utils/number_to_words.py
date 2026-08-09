"""
Amount in Words Converter Utility
Supports Thai BahtText (บาทถ้วน/สตางค์) and English Currency Words (USD / THB / EUR)
100% ERP Grade Financial Compliance
"""

def thai_baht_text(amount: float) -> str:
    """
    Converts numeric amount into official Thai Baht text (เช่น หนึ่งพันห้าร้อยบาทถ้วน).
    """
    if amount is None:
        return "ศูนย์บาทถ้วน"

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return "ศูนย์บาทถ้วน"

    if amount == 0:
        return "ศูนย์บาทถ้วน"

    num_text = ["ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
    unit_text = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"]

    baht_part = int(abs(amount))
    satang_part = int(round((abs(amount) - baht_part) * 100))

    def convert_section(n: int) -> str:
        s = str(n)
        length = len(s)
        res = []
        for i, ch in enumerate(s):
            digit = int(ch)
            pos = length - i - 1
            if digit != 0:
                if pos == 1 and digit == 1:
                    res.append("สิบ")
                elif pos == 1 and digit == 2:
                    res.append("ยี่สิบ")
                elif pos == 0 and digit == 1 and length > 1:
                    res.append("เอ็ด")
                else:
                    res.append(num_text[digit] + unit_text[pos])
        return "".join(res)

    result = []
    if amount < 0:
        result.append("ลบ")

    str_baht = str(baht_part)
    groups = []
    while len(str_baht) > 6:
        groups.insert(0, int(str_baht[-6:]))
        str_baht = str_baht[:-6]
    if str_baht:
        groups.insert(0, int(str_baht))

    for idx, grp in enumerate(groups):
        grp_text = convert_section(grp)
        result.append(grp_text)
        if idx < len(groups) - 1:
            result.append("ล้าน")

    result.append("บาท")

    if satang_part == 0:
        result.append("ถ้วน")
    else:
        result.append(convert_section(satang_part) + "สตางค์")

    return "".join(result)


def number_to_english_words(amount: float, currency: str = "USD") -> str:
    """
    Converts numeric amount into English Currency Words (e.g. SAY ONE THOUSAND FIVE HUNDRED US DOLLARS ONLY).
    """
    if amount is None:
        return "SAY ZERO DOLLARS ONLY"

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return "SAY ZERO DOLLARS ONLY"

    units = ["", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
             "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN", "NINETEEN"]
    tens = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]

    def _convert_hundreds(n: int) -> str:
        res = []
        if n >= 100:
            res.append(units[n // 100] + " HUNDRED")
            n %= 100
        if n >= 20:
            t = tens[n // 10]
            u = units[n % 10]
            res.append(f"{t}-{u}" if u else t)
        elif n > 0:
            res.append(units[n])
        return " ".join(res)

    int_part = int(abs(amount))
    cents_part = int(round((abs(amount) - int_part) * 100))

    if int_part == 0:
        words = "ZERO"
    else:
        parts = []
        billions = int_part // 1_000_000_000
        millions = (int_part % 1_000_000_000) // 1_000_000
        thousands = (int_part % 1_000_000) // 1_000
        rem = int_part % 1_000

        if billions:
            parts.append(_convert_hundreds(billions) + " BILLION")
        if millions:
            parts.append(_convert_hundreds(millions) + " MILLION")
        if thousands:
            parts.append(_convert_hundreds(thousands) + " THOUSAND")
        if rem:
            parts.append(_convert_hundreds(rem))

        words = " ".join(parts)

    curr_name = currency.upper()
    if curr_name == "USD":
        main_unit, sub_unit = "US DOLLARS", "CENTS"
    elif curr_name == "THB":
        main_unit, sub_unit = "BAHT", "SATANG"
    elif curr_name == "EUR":
        main_unit, sub_unit = "EUROS", "CENTS"
    else:
        main_unit, sub_unit = curr_name, "CENTS"

    if cents_part > 0:
        cents_words = _convert_hundreds(cents_part)
        return f"SAY {words} {main_unit} AND {cents_words} {sub_unit} ONLY"
    else:
        return f"SAY {words} {main_unit} ONLY"
