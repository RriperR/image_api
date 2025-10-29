from __future__ import annotations

from typing import Optional


class ValidationError(Exception):
    pass


def parse_optional_int(name: str, raw: Optional[str], *, min_value: int, max_value: int) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be integer") from exc
    if not (min_value <= value <= max_value):
        raise ValidationError(f"{name} must be in range [{min_value}; {max_value}]")
    return value
