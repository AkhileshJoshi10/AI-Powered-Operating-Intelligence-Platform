from __future__ import annotations

from collections.abc import Mapping
from math import isnan

from backend.analytics.date_utils import normalize_text


def is_missing(value: object) -> bool:
    """Return True when a value should be excluded from evidence text."""

    if value is None:
        return True

    if isinstance(value, float) and isnan(value):
        return True

    if isinstance(value, str):
        return not normalize_text(value)

    return False


def format_currency(value: object) -> str:
    """Format a numeric value as Indian currency-style text."""

    if is_missing(value):
        return "Not available"

    return f"₹{float(value):,.2f}"


def format_percent(value: object) -> str:
    """Format a numeric value as a percentage."""

    if is_missing(value):
        return "Not available"

    return f"{float(value):.2f}%"


def build_evidence(items: Mapping[str, object]) -> str:
    """Build one consistent evidence string from labelled values."""

    evidence_parts = []

    for label, value in items.items():
        if is_missing(value):
            continue

        evidence_parts.append(f"{label}: {value}")

    return "; ".join(evidence_parts)