from __future__ import annotations

import pandas as pd

from backend.analytics.kpi_calculator import build_kpi_summary
from backend.app.db.database import engine


def clean_text(value: object) -> str:
    """Convert a database or pandas value safely to text."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip()


def clean_float(value: object) -> float:
    """Convert a database or pandas value safely to float."""

    if value is None:
        return 0.0

    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        return 0.0

    return round(float(value), 2)


def get_kpi_response() -> dict:
    """Calculate and return the current KPI API response."""

    kpi_dataframe, store_target_dataframe = build_kpi_summary(
        engine
    )

    kpi_records = []

    for row in kpi_dataframe.itertuples(index=False):
        kpi_records.append(
            {
                "kpi_key": clean_text(row.kpi_key),
                "kpi_name": clean_text(row.kpi_name),
                "value": clean_float(row.value),
                "display_value": clean_text(row.display_value),
                "unit": clean_text(row.unit),
                "reference_period": clean_text(
                    row.reference_period
                ),
                "description": clean_text(row.description),
                "calculated_at": clean_text(row.calculated_at),
            }
        )

    store_target_records = []

    for row in store_target_dataframe.itertuples(index=False):
        store_target_records.append(
            {
                "store_id": clean_text(row.store_id),
                "store_name": clean_text(row.store_name),
                "month": clean_text(row.month),
                "monthly_sales_target": clean_float(
                    row.monthly_sales_target
                ),
                "total_revenue": clean_float(row.total_revenue),
                "operating_profit": clean_float(
                    row.operating_profit
                ),
                "target_achievement_percent": clean_float(
                    row.target_achievement_percent
                ),
                "risk_status": clean_text(row.risk_status),
            }
        )

    return {
        "status": "success",
        "total_kpis": len(kpi_records),
        "kpis": kpi_records,
        "latest_store_target_achievement": (
            store_target_records
        ),
    }