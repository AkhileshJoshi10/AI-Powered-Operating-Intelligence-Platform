from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "raw"
REPORT_DIR = BASE_DIR / "reports"

RAW_DATASET_FILES = {
    "products": "products_data.csv",
    "stores": "stores_data.csv",
    "vendors": "vendors_data.csv",
    "employees": "employees_data.csv",
    "sales": "sales_data.csv",
    "inventory": "inventory_data.csv",
    "complaints": "complaints_data.csv",
    "finance": "finance_data.csv",
    "vendor_deliveries": "vendor_deliveries_data.csv",
}


@dataclass
class ValidationContext:
    """Mutable state used during one validation run."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)


def load_dataset(
    *,
    filename: str,
    data_directory: Path,
    context: ValidationContext,
    dataset_overrides: dict[str, pd.DataFrame],
) -> pd.DataFrame | None:
    """Load one CSV or use an in-memory replacement DataFrame."""

    if filename in dataset_overrides:
        dataframe = dataset_overrides[filename].copy()

        context.summary.append(
            f"{filename}: {len(dataframe)} rows, "
            f"{len(dataframe.columns)} columns"
        )

        return dataframe

    file_path = data_directory / filename

    if not file_path.exists():
        context.warnings.append(
            f"File not found (skipped): {filename}"
        )
        return None

    try:
        dataframe = pd.read_csv(file_path)

    except (
        OSError,
        UnicodeDecodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as error:
        context.errors.append(
            f"{filename}: Could not read CSV file -> {error}"
        )
        return None

    context.summary.append(
        f"{filename}: {len(dataframe)} rows, "
        f"{len(dataframe.columns)} columns"
    )

    return dataframe


def clean_missing_values(series: pd.Series) -> pd.Series:
    """Return a Boolean mask identifying missing values."""

    text_series = series.astype(str).str.strip()

    return (
        series.isna()
        | text_series.str.lower().isin(
            [
                "",
                "na",
                "n/a",
                "none",
                "nan",
            ]
        )
    )


def check_required_columns(
    dataframe: pd.DataFrame | None,
    dataset_name: str,
    required_columns: list[str],
    context: ValidationContext,
) -> None:
    """Check whether a dataset contains its required columns."""

    if dataframe is None:
        return

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        context.errors.append(
            f"{dataset_name}: Missing columns -> {missing_columns}"
        )


def check_duplicate_ids(
    dataframe: pd.DataFrame | None,
    dataset_name: str,
    id_column: str,
    context: ValidationContext,
) -> None:
    """Check whether a primary identifier contains duplicates."""

    if dataframe is None or id_column not in dataframe.columns:
        return

    duplicate_count = int(
        dataframe[id_column].duplicated().sum()
    )

    if duplicate_count > 0:
        context.errors.append(
            f"{dataset_name}: {duplicate_count} duplicate values "
            f"found in {id_column}"
        )


def check_missing_values(
    dataframe: pd.DataFrame | None,
    dataset_name: str,
    required_columns: list[str],
    context: ValidationContext,
) -> None:
    """Check required fields for blank or missing values."""

    if dataframe is None:
        return

    for column in required_columns:
        if column not in dataframe.columns:
            continue

        missing_count = int(
            clean_missing_values(dataframe[column]).sum()
        )

        if missing_count > 0:
            context.errors.append(
                f"{dataset_name}: {missing_count} missing values "
                f"in {column}"
            )


def check_foreign_key(
    child_dataframe: pd.DataFrame | None,
    child_name: str,
    child_column: str,
    parent_dataframe: pd.DataFrame | None,
    parent_name: str,
    parent_column: str,
    context: ValidationContext,
) -> None:
    """Check whether child values exist in the parent dataset."""

    if child_dataframe is None or parent_dataframe is None:
        return

    if child_column not in child_dataframe.columns:
        context.warnings.append(
            f"{child_name}: Relationship column not found -> "
            f"{child_column}"
        )
        return

    if parent_column not in parent_dataframe.columns:
        context.warnings.append(
            f"{parent_name}: Relationship column not found -> "
            f"{parent_column}"
        )
        return

    child_missing_mask = clean_missing_values(
        child_dataframe[child_column]
    )

    valid_child_values = child_dataframe.loc[
        ~child_missing_mask,
        child_column,
    ]

    parent_values = parent_dataframe[parent_column].dropna()

    invalid_values = valid_child_values[
        ~valid_child_values.isin(parent_values)
    ].unique()

    if len(invalid_values) > 0:
        context.errors.append(
            f"{child_name}: Invalid {child_column} values not found "
            f"in {parent_name} -> {list(invalid_values[:10])}"
        )


def get_numeric_series(
    dataframe: pd.DataFrame | None,
    dataset_name: str,
    column: str,
    context: ValidationContext,
) -> pd.Series | None:
    """Convert a column into numeric values and report invalid data."""

    if dataframe is None or column not in dataframe.columns:
        return None

    raw_series = dataframe[column]
    missing_mask = clean_missing_values(raw_series)

    numeric_series = pd.to_numeric(
        raw_series.where(~missing_mask),
        errors="coerce",
    )

    invalid_mask = (
        ~missing_mask
        & numeric_series.isna()
    )

    invalid_count = int(invalid_mask.sum())

    if invalid_count > 0:
        invalid_values = (
            raw_series[invalid_mask]
            .head(5)
            .tolist()
        )

        context.errors.append(
            f"{dataset_name}: Non-numeric values found in "
            f"{column} -> {invalid_values}"
        )

    return numeric_series


def check_non_negative(
    dataframe: pd.DataFrame | None,
    dataset_name: str,
    columns: list[str],
    context: ValidationContext,
) -> None:
    """Check numeric columns for negative values."""

    if dataframe is None:
        return

    for column in columns:
        if column not in dataframe.columns:
            continue

        numeric_series = get_numeric_series(
            dataframe,
            dataset_name,
            column,
            context,
        )

        if numeric_series is None:
            continue

        negative_count = int(
            (numeric_series < 0).sum()
        )

        if negative_count > 0:
            context.errors.append(
                f"{dataset_name}: {negative_count} negative values "
                f"found in {column}"
            )


def parse_date_column(
    dataframe: pd.DataFrame | None,
    dataset_name: str,
    column: str,
    context: ValidationContext,
) -> pd.Series | None:
    """Parse a raw-data date column using DD-MM-YY format."""

    if dataframe is None or column not in dataframe.columns:
        return None

    raw_series = dataframe[column]
    missing_mask = clean_missing_values(raw_series)

    date_series = pd.to_datetime(
        raw_series.where(~missing_mask),
        format="%d-%m-%y",
        errors="coerce",
    )

    invalid_mask = (
        ~missing_mask
        & date_series.isna()
    )

    invalid_count = int(invalid_mask.sum())

    if invalid_count > 0:
        invalid_values = (
            raw_series[invalid_mask]
            .head(5)
            .tolist()
        )

        context.errors.append(
            f"{dataset_name}: Invalid date values found in "
            f"{column} -> {invalid_values}"
        )

    return date_series


def check_inventory_status_logic(
    inventory_dataframe: pd.DataFrame | None,
    context: ValidationContext,
) -> None:
    """Validate inventory stock status and reorder logic."""

    if inventory_dataframe is None:
        return

    required_columns = [
        "current_stock",
        "reorder_level",
        "stock_status",
    ]

    if not all(
        column in inventory_dataframe.columns
        for column in required_columns
    ):
        context.warnings.append(
            "inventory_data.csv: Stock-status validation skipped "
            "because required columns are missing."
        )
        return

    current_stock = get_numeric_series(
        inventory_dataframe,
        "inventory_data.csv",
        "current_stock",
        context,
    )

    reorder_level = get_numeric_series(
        inventory_dataframe,
        "inventory_data.csv",
        "reorder_level",
        context,
    )

    if current_stock is None or reorder_level is None:
        return

    actual_status = (
        inventory_dataframe["stock_status"]
        .astype(str)
        .str.strip()
    )

    expected_status = pd.Series(
        np.select(
            [
                current_stock < (reorder_level * 0.80),
                current_stock < reorder_level,
                current_stock > (reorder_level * 3),
            ],
            [
                "Low Stock",
                "Reorder Soon",
                "Overstock",
            ],
            default="Normal",
        ),
        index=inventory_dataframe.index,
    )

    valid_numeric_mask = (
        current_stock.notna()
        & reorder_level.notna()
    )

    mismatch_mask = (
        valid_numeric_mask
        & actual_status.ne(expected_status)
    )

    mismatch_count = int(mismatch_mask.sum())

    if mismatch_count > 0:
        sample_columns = [
            column
            for column in [
                "inventory_id",
                "current_stock",
                "reorder_level",
                "stock_status",
            ]
            if column in inventory_dataframe.columns
        ]

        sample_rows = inventory_dataframe.loc[
            mismatch_mask,
            sample_columns,
        ].head(5)

        context.errors.append(
            "inventory_data.csv: Stock-status logic mismatch "
            f"found in {mismatch_count} rows.\n"
            f"{sample_rows.to_string(index=False)}"
        )

    if "reorder_required" not in inventory_dataframe.columns:
        return

    actual_reorder = (
        inventory_dataframe["reorder_required"]
        .astype(str)
        .str.strip()
    )

    expected_reorder = pd.Series(
        np.where(
            expected_status.eq("Low Stock"),
            "Yes",
            "No",
        ),
        index=inventory_dataframe.index,
    )

    reorder_mismatch_mask = (
        valid_numeric_mask
        & actual_reorder.ne(expected_reorder)
    )

    reorder_mismatch_count = int(
        reorder_mismatch_mask.sum()
    )

    if reorder_mismatch_count > 0:
        context.errors.append(
            "inventory_data.csv: reorder_required logic mismatch "
            f"found in {reorder_mismatch_count} rows."
        )


def check_expiry_dates(
    inventory_dataframe: pd.DataFrame | None,
    context: ValidationContext,
) -> None:
    """Check that expiry dates are not before inventory dates."""

    if inventory_dataframe is None:
        return

    if "expiry_date" not in inventory_dataframe.columns:
        context.warnings.append(
            "inventory_data.csv: Expiry-date validation skipped "
            "because expiry_date column is missing."
        )
        return

    reference_date_column = None

    for possible_column in [
        "date",
        "inventory_date",
        "record_date",
        "stock_date",
        "last_restock_date",
    ]:
        if possible_column in inventory_dataframe.columns:
            reference_date_column = possible_column
            break

    if reference_date_column is None:
        context.warnings.append(
            "inventory_data.csv: Expiry-date validation skipped "
            "because no inventory/reference date column was found."
        )
        return

    expiry_date = parse_date_column(
        inventory_dataframe,
        "inventory_data.csv",
        "expiry_date",
        context,
    )

    reference_date = parse_date_column(
        inventory_dataframe,
        "inventory_data.csv",
        reference_date_column,
        context,
    )

    if expiry_date is None or reference_date is None:
        return

    expired_mask = (
        expiry_date.notna()
        & reference_date.notna()
        & expiry_date.lt(reference_date)
    )

    expired_count = int(expired_mask.sum())

    if expired_count > 0:
        sample_columns = [
            column
            for column in [
                "inventory_id",
                reference_date_column,
                "expiry_date",
            ]
            if column in inventory_dataframe.columns
        ]

        sample_rows = inventory_dataframe.loc[
            expired_mask,
            sample_columns,
        ].head(5)

        context.errors.append(
            "inventory_data.csv: Expiry date is before record date "
            f"in {expired_count} rows.\n"
            f"{sample_rows.to_string(index=False)}"
        )


def check_finance_calculations(
    finance_dataframe: pd.DataFrame | None,
    context: ValidationContext,
) -> None:
    """Validate gross-profit and operating-profit calculations."""

    if finance_dataframe is None:
        return

    required_columns = [
        "total_revenue",
        "total_cost",
        "gross_profit",
        "operating_expense",
        "operating_profit",
    ]

    if not all(
        column in finance_dataframe.columns
        for column in required_columns
    ):
        context.warnings.append(
            "finance_data.csv: Finance-calculation validation "
            "skipped because required columns are missing."
        )
        return

    total_revenue = get_numeric_series(
        finance_dataframe,
        "finance_data.csv",
        "total_revenue",
        context,
    )

    total_cost = get_numeric_series(
        finance_dataframe,
        "finance_data.csv",
        "total_cost",
        context,
    )

    gross_profit = get_numeric_series(
        finance_dataframe,
        "finance_data.csv",
        "gross_profit",
        context,
    )

    operating_expense = get_numeric_series(
        finance_dataframe,
        "finance_data.csv",
        "operating_expense",
        context,
    )

    operating_profit = get_numeric_series(
        finance_dataframe,
        "finance_data.csv",
        "operating_profit",
        context,
    )

    if any(
        value is None
        for value in [
            total_revenue,
            total_cost,
            gross_profit,
            operating_expense,
            operating_profit,
        ]
    ):
        return

    expected_gross_profit = (
        total_revenue
        - total_cost
    )

    gross_profit_error = (
        gross_profit
        - expected_gross_profit
    ).abs().gt(1)

    gross_profit_error_count = int(
        gross_profit_error.sum()
    )

    if gross_profit_error_count > 0:
        context.errors.append(
            "finance_data.csv: gross_profit calculation mismatch "
            f"found in {gross_profit_error_count} rows."
        )

    expected_operating_profit = (
        gross_profit
        - operating_expense
    )

    operating_profit_error = (
        operating_profit
        - expected_operating_profit
    ).abs().gt(1)

    operating_profit_error_count = int(
        operating_profit_error.sum()
    )

    if operating_profit_error_count > 0:
        context.errors.append(
            "finance_data.csv: operating_profit calculation "
            f"mismatch found in {operating_profit_error_count} rows."
        )


def check_vendor_delivery_logic(
    vendor_deliveries_dataframe: pd.DataFrame | None,
    context: ValidationContext,
) -> None:
    """Validate delivery dates and calculated delay days."""

    if vendor_deliveries_dataframe is None:
        return

    required_columns = [
        "order_date",
        "expected_delivery_date",
        "actual_delivery_date",
        "delay_days",
    ]

    if not all(
        column in vendor_deliveries_dataframe.columns
        for column in required_columns
    ):
        context.warnings.append(
            "vendor_deliveries_data.csv: Delivery-date validation "
            "skipped because required columns are missing."
        )
        return

    order_date = parse_date_column(
        vendor_deliveries_dataframe,
        "vendor_deliveries_data.csv",
        "order_date",
        context,
    )

    expected_date = parse_date_column(
        vendor_deliveries_dataframe,
        "vendor_deliveries_data.csv",
        "expected_delivery_date",
        context,
    )

    actual_date = parse_date_column(
        vendor_deliveries_dataframe,
        "vendor_deliveries_data.csv",
        "actual_delivery_date",
        context,
    )

    delay_days = get_numeric_series(
        vendor_deliveries_dataframe,
        "vendor_deliveries_data.csv",
        "delay_days",
        context,
    )

    if any(
        value is None
        for value in [
            order_date,
            expected_date,
            actual_date,
            delay_days,
        ]
    ):
        return

    before_order_mask = (
        actual_date.notna()
        & order_date.notna()
        & actual_date.lt(order_date)
    )

    before_order_count = int(
        before_order_mask.sum()
    )

    if before_order_count > 0:
        context.errors.append(
            "vendor_deliveries_data.csv: Actual delivery date is "
            f"before order date in {before_order_count} rows."
        )

    calculated_delay = (
        actual_date
        - expected_date
    ).dt.days

    delay_error = (
        calculated_delay.notna()
        & delay_days.notna()
        & calculated_delay.sub(delay_days).abs().gt(0)
    )

    delay_error_count = int(delay_error.sum())

    if delay_error_count > 0:
        context.errors.append(
            "vendor_deliveries_data.csv: delay_days does not match "
            "actual and expected delivery dates in "
            f"{delay_error_count} rows."
        )


def run_validation_checks(
    datasets: dict[str, pd.DataFrame | None],
    context: ValidationContext,
) -> None:
    """Run all structural, relational and business-rule checks."""

    products = datasets["products"]
    stores = datasets["stores"]
    vendors = datasets["vendors"]
    employees = datasets["employees"]
    sales = datasets["sales"]
    inventory = datasets["inventory"]
    complaints = datasets["complaints"]
    finance = datasets["finance"]
    vendor_deliveries = datasets["vendor_deliveries"]

    required_column_checks = [
        (
            products,
            "products_data.csv",
            [
                "product_id",
                "product_name",
                "vendor_id",
                "unit_price",
                "cost_price",
            ],
        ),
        (
            stores,
            "stores_data.csv",
            [
                "store_id",
                "store_name",
                "manager_id",
                "monthly_sales_target",
            ],
        ),
        (
            vendors,
            "vendors_data.csv",
            [
                "vendor_id",
                "vendor_name",
                "average_delivery_days",
                "rating",
            ],
        ),
        (
            employees,
            "employees_data.csv",
            [
                "employee_id",
                "employee_name",
                "role",
                "store_id",
            ],
        ),
        (
            sales,
            "sales_data.csv",
            [
                "sale_id",
                "date",
                "store_id",
                "product_id",
                "employee_id",
                "total_sales",
            ],
        ),
        (
            inventory,
            "inventory_data.csv",
            [
                "inventory_id",
                "date",
                "store_id",
                "product_id",
                "vendor_id",
                "current_stock",
            ],
        ),
        (
            complaints,
            "complaints_data.csv",
            [
                "complaint_id",
                "date",
                "store_id",
                "product_id",
                "severity",
                "status",
            ],
        ),
        (
            finance,
            "finance_data.csv",
            [
                "finance_id",
                "month",
                "store_id",
                "total_revenue",
                "gross_profit",
                "operating_profit",
                "risk_status",
            ],
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            [
                "purchase_order_id",
                "store_id",
                "vendor_id",
                "product_id",
                "delay_days",
                "delivery_status",
            ],
        ),
    ]

    for (
        dataframe,
        dataset_name,
        required_columns,
    ) in required_column_checks:
        check_required_columns(
            dataframe,
            dataset_name,
            required_columns,
            context,
        )

    duplicate_checks = [
        (products, "products_data.csv", "product_id"),
        (stores, "stores_data.csv", "store_id"),
        (vendors, "vendors_data.csv", "vendor_id"),
        (employees, "employees_data.csv", "employee_id"),
        (sales, "sales_data.csv", "sale_id"),
        (inventory, "inventory_data.csv", "inventory_id"),
        (complaints, "complaints_data.csv", "complaint_id"),
        (finance, "finance_data.csv", "finance_id"),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            "purchase_order_id",
        ),
    ]

    for (
        dataframe,
        dataset_name,
        id_column,
    ) in duplicate_checks:
        check_duplicate_ids(
            dataframe,
            dataset_name,
            id_column,
            context,
        )

    missing_value_checks = [
        (
            products,
            "products_data.csv",
            ["product_id", "vendor_id"],
        ),
        (
            stores,
            "stores_data.csv",
            ["store_id", "manager_id"],
        ),
        (
            vendors,
            "vendors_data.csv",
            ["vendor_id"],
        ),
        (
            employees,
            "employees_data.csv",
            ["employee_id"],
        ),
        (
            sales,
            "sales_data.csv",
            [
                "sale_id",
                "store_id",
                "product_id",
            ],
        ),
        (
            inventory,
            "inventory_data.csv",
            [
                "inventory_id",
                "date",
                "store_id",
                "product_id",
            ],
        ),
        (
            complaints,
            "complaints_data.csv",
            [
                "complaint_id",
                "store_id",
            ],
        ),
        (
            finance,
            "finance_data.csv",
            [
                "finance_id",
                "store_id",
            ],
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            [
                "purchase_order_id",
                "store_id",
                "vendor_id",
                "product_id",
            ],
        ),
    ]

    for (
        dataframe,
        dataset_name,
        required_columns,
    ) in missing_value_checks:
        check_missing_values(
            dataframe,
            dataset_name,
            required_columns,
            context,
        )

    foreign_key_checks = [
        (
            products,
            "products_data.csv",
            "vendor_id",
            vendors,
            "vendors_data.csv",
            "vendor_id",
        ),
        (
            stores,
            "stores_data.csv",
            "manager_id",
            employees,
            "employees_data.csv",
            "employee_id",
        ),
        (
            sales,
            "sales_data.csv",
            "store_id",
            stores,
            "stores_data.csv",
            "store_id",
        ),
        (
            sales,
            "sales_data.csv",
            "product_id",
            products,
            "products_data.csv",
            "product_id",
        ),
        (
            sales,
            "sales_data.csv",
            "employee_id",
            employees,
            "employees_data.csv",
            "employee_id",
        ),
        (
            inventory,
            "inventory_data.csv",
            "store_id",
            stores,
            "stores_data.csv",
            "store_id",
        ),
        (
            inventory,
            "inventory_data.csv",
            "product_id",
            products,
            "products_data.csv",
            "product_id",
        ),
        (
            inventory,
            "inventory_data.csv",
            "vendor_id",
            vendors,
            "vendors_data.csv",
            "vendor_id",
        ),
        (
            complaints,
            "complaints_data.csv",
            "store_id",
            stores,
            "stores_data.csv",
            "store_id",
        ),
        (
            complaints,
            "complaints_data.csv",
            "product_id",
            products,
            "products_data.csv",
            "product_id",
        ),
        (
            finance,
            "finance_data.csv",
            "store_id",
            stores,
            "stores_data.csv",
            "store_id",
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            "store_id",
            stores,
            "stores_data.csv",
            "store_id",
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            "vendor_id",
            vendors,
            "vendors_data.csv",
            "vendor_id",
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            "product_id",
            products,
            "products_data.csv",
            "product_id",
        ),
    ]

    for foreign_key_check in foreign_key_checks:
        check_foreign_key(
            *foreign_key_check,
            context,
        )

    numeric_checks = [
        (
            products,
            "products_data.csv",
            [
                "unit_price",
                "cost_price",
                "margin_percent",
                "reorder_level",
            ],
        ),
        (
            stores,
            "stores_data.csv",
            ["monthly_sales_target"],
        ),
        (
            vendors,
            "vendors_data.csv",
            [
                "average_delivery_days",
                "rating",
            ],
        ),
        (
            sales,
            "sales_data.csv",
            [
                "quantity_sold",
                "unit_price",
                "discount_percent",
                "total_sales",
                "total_cost",
            ],
        ),
        (
            inventory,
            "inventory_data.csv",
            [
                "current_stock",
                "reorder_level",
            ],
        ),
        (
            finance,
            "finance_data.csv",
            [
                "monthly_sales_target",
                "total_revenue",
                "total_cost",
                "gross_profit",
                "operating_expense",
            ],
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            [
                "ordered_quantity",
                "received_quantity",
                "unit_cost",
                "purchase_value",
                "delay_days",
                "quality_rating",
            ],
        ),
    ]

    for (
        dataframe,
        dataset_name,
        columns,
    ) in numeric_checks:
        check_non_negative(
            dataframe,
            dataset_name,
            columns,
            context,
        )

    date_checks = [
        (
            stores,
            "stores_data.csv",
            "opening_date",
        ),
        (
            sales,
            "sales_data.csv",
            "date",
        ),
        (
            inventory,
            "inventory_data.csv",
            "date",
        ),
        (
            complaints,
            "complaints_data.csv",
            "date",
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            "order_date",
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            "expected_delivery_date",
        ),
        (
            vendor_deliveries,
            "vendor_deliveries_data.csv",
            "actual_delivery_date",
        ),
    ]

    for (
        dataframe,
        dataset_name,
        column,
    ) in date_checks:
        parse_date_column(
            dataframe,
            dataset_name,
            column,
            context,
        )

    check_inventory_status_logic(
        inventory,
        context,
    )

    check_expiry_dates(
        inventory,
        context,
    )

    check_finance_calculations(
        finance,
        context,
    )

    check_vendor_delivery_logic(
        vendor_deliveries,
        context,
    )


def build_validation_report(
    context: ValidationContext,
) -> str:
    """Build the plain-text validation report."""

    report_lines = [
        "DATA VALIDATION REPORT",
        "=" * 50,
        "",
        "DATASET SUMMARY",
    ]

    if context.summary:
        report_lines.extend(context.summary)
    else:
        report_lines.append("No datasets were loaded.")

    report_lines.extend(
        [
            "",
            "ERRORS",
        ]
    )

    if context.errors:
        report_lines.extend(context.errors)
    else:
        report_lines.append(
            "No validation errors found."
        )

    report_lines.extend(
        [
            "",
            "WARNINGS",
        ]
    )

    if context.warnings:
        report_lines.extend(context.warnings)
    else:
        report_lines.append(
            "No warnings found."
        )

    return "\n".join(report_lines)


def validate_raw_datasets(
    *,
    data_directory: Path | None = None,
    dataset_overrides: dict[str, pd.DataFrame] | None = None,
    write_report: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """
    Validate the nine raw business datasets.

    dataset_overrides can temporarily replace one or more raw CSVs
    without changing files on disk. Keys must be raw CSV filenames,
    such as sales_data.csv.
    """

    selected_data_directory = (
        data_directory
        if data_directory is not None
        else DATA_DIR
    )

    selected_overrides = (
        dataset_overrides
        if dataset_overrides is not None
        else {}
    )

    context = ValidationContext()

    datasets = {
        dataset_name: load_dataset(
            filename=filename,
            data_directory=selected_data_directory,
            context=context,
            dataset_overrides=selected_overrides,
        )
        for dataset_name, filename
        in RAW_DATASET_FILES.items()
    }

    run_validation_checks(
        datasets,
        context,
    )

    report_text = build_validation_report(
        context
    )

    saved_report_path: Path | None = None

    if write_report:
        REPORT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved_report_path = (
            report_path
            if report_path is not None
            else REPORT_DIR / "data_validation_report.txt"
        )

        saved_report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved_report_path.write_text(
            report_text,
            encoding="utf-8",
        )

    return {
        "is_valid": len(context.errors) == 0,
        "error_count": len(context.errors),
        "warning_count": len(context.warnings),
        "errors": context.errors,
        "warnings": context.warnings,
        "summary": context.summary,
        "report_text": report_text,
        "report_path": (
            str(saved_report_path)
            if saved_report_path is not None
            else None
        ),
    }


def main() -> None:
    """Run validation from the command line and save the report."""

    validation_result = validate_raw_datasets(
        write_report=True,
    )

    print(validation_result["report_text"])

    print("\nValidation report saved at:")
    print(validation_result["report_path"])


if __name__ == "__main__":
    main()