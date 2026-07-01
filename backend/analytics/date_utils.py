from __future__ import annotations

import re
from datetime import date, datetime


YEAR_MONTH_PATTERN = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def normalize_text(value: object) -> str:
    """Remove extra spaces and return clean text."""

    if value is None:
        return ""

    return " ".join(str(value).split())


def extract_year_month_from_issue_id(issue_id: object) -> str:
    """Extract YYYY-MM from an issue ID such as FIN-S003-2026-06."""

    clean_issue_id = normalize_text(issue_id)
    matches = YEAR_MONTH_PATTERN.findall(clean_issue_id)

    if not matches:
        raise ValueError(
            f"Could not find a YYYY-MM value in issue ID: {clean_issue_id}"
        )

    year_month_match = re.search(r"\d{4}-(0[1-9]|1[0-2])", clean_issue_id)

    if year_month_match is None:
        raise ValueError(
            f"Could not extract a valid YYYY-MM value from: {clean_issue_id}"
        )

    return year_month_match.group(0)


def parse_iso_date(value: object) -> date | None:
    """Convert an ISO date-like value into a Python date object."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    clean_value = normalize_text(value)

    if not clean_value or clean_value.lower() in {"nan", "nat", "none"}:
        return None

    return datetime.strptime(clean_value, "%Y-%m-%d").date()


def days_between(
    reference_date: object,
    target_date: object,
) -> int | None:
    """Return target_date minus reference_date in days."""

    start_date = parse_iso_date(reference_date)
    end_date = parse_iso_date(target_date)

    if start_date is None or end_date is None:
        return None

    return (end_date - start_date).days