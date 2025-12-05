from typing import Any


def safe_str(value: Any, max_len: int) -> str:
    if value is None:
        return ""
    return str(value)[:max_len]


def safe_int(value: Any):
    try:
        return int(value)
    except Exception:
        return None


def safe_float(value: Any):
    try:
        return float(value)
    except Exception:
        return None