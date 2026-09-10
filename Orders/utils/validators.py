from typing import Tuple


def validate_product_record(p: dict) -> Tuple[bool, str]:
    offer = p.get('offer_id') or p.get('sku')
    if not offer or not isinstance(offer, str):
        return False, "offer_id/sku отсутствует или не строка"

    name = p.get('name')
    if not isinstance(name, str) or not name.strip():
        return False, "name отсутствует или не строка"

    try:
        if float(p.get('price', {}).get('amount')) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return False, f"price некорректное: {p.get('price')}"

    try:
        if int(p.get('quantity')) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return False, f"quantity некорректное: {p.get('quantity')}"

    return True, ""
