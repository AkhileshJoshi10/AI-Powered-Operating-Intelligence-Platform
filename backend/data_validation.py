import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "raw"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(exist_ok=True)

errors = []
warnings = []
summary = []


def load_dataset(filename):
    file_path = DATA_DIR / filename

    if not file_path.exists():
        warnings.append(f"File not found (skipped): {filename}")
        return None

    df = pd.read_csv(file_path)
    summary.append(f"{filename}: {len(df)} rows, {len(df.columns)} columns")
    return df


def clean_missing_values(series):
    text_series = series.astype(str).str.strip()

    return (
        series.isna()
        | text_series.str.lower().isin(["", "na", "n/a", "none", "nan"])
    )


def check_required_columns(df, dataset_name, required_columns):
    if df is None:
        return

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        errors.append(
            f"{dataset_name}: Missing columns -> {missing_columns}"
        )


def check_duplicate_ids(df, dataset_name, id_column):
    if df is None or id_column not in df.columns:
        return

    duplicate_count = df[id_column].duplicated().sum()

    if duplicate_count > 0:
        errors.append(
            f"{dataset_name}: {duplicate_count} duplicate values found in {id_column}"
        )


def check_missing_values(df, dataset_name, required_columns):
    if df is None:
        return

    for column in required_columns:
        if column in df.columns:
            missing_count = clean_missing_values(df[column]).sum()

            if missing_count > 0:
                errors.append(
                    f"{dataset_name}: {missing_count} missing values in {column}"
                )


def check_foreign_key(
    child_df,
    child_name,
    child_column,
    parent_df,
    parent_name,
    parent_column
):
    if child_df is None or parent_df is None:
        return

    if child_column not in child_df.columns:
        warnings.append(
            f"{child_name}: Relationship column not found -> {child_column}"
        )
        return

    if parent_column not in parent_df.columns:
        warnings.append(
            f"{parent_name}: Relationship column not found -> {parent_column}"
        )
        return

    invalid_values = child_df[
        ~child_df[child_column].isin(parent_df[parent_column])
    ][child_column].dropna().unique()

    if len(invalid_values) > 0:
        errors.append(
            f"{child_name}: Invalid {child_column} values not found in "
            f"{parent_name} -> {list(invalid_values[:10])}"
        )


def get_numeric_series(df, dataset_name, column):
    if df is None or column not in df.columns:
        return None

    raw_series = df[column]
    missing_mask = clean_missing_values(raw_series)

    numeric_series = pd.to_numeric(
        raw_series.where(~missing_mask),
        errors="coerce"
    )

    invalid_mask = (~missing_mask) & numeric_series.isna()

    if invalid_mask.sum() > 0:
        invalid_values = raw_series[invalid_mask].head(5).tolist()

        errors.append(
            f"{dataset_name}: Non-numeric values found in {column} -> "
            f"{invalid_values}"
        )

    return numeric_series


def check_non_negative(df, dataset_name, columns):
    if df is None:
        return

    for column in columns:
        if column not in df.columns:
            continue

        numeric_series = get_numeric_series(df, dataset_name, column)

        if numeric_series is None:
            continue

        negative_count = (numeric_series < 0).sum()

        if negative_count > 0:
            errors.append(
                f"{dataset_name}: {negative_count} negative values found in {column}"
            )


def parse_date_column(df, dataset_name, column):
    if df is None or column not in df.columns:
        return None

    raw_series = df[column]
    missing_mask = clean_missing_values(raw_series)

    date_series = pd.to_datetime(
        raw_series.where(~missing_mask),
        format="%d-%m-%y",
        errors="coerce"
    )

    invalid_mask = (~missing_mask) & date_series.isna()

    if invalid_mask.sum() > 0:
        invalid_values = raw_series[invalid_mask].head(5).tolist()

        errors.append(
            f"{dataset_name}: Invalid date values found in {column} -> "
            f"{invalid_values}"
        )

    return date_series


def check_inventory_status_logic(inventory_df):
    if inventory_df is None:
        return

    required_columns = [
        "current_stock",
        "reorder_level",
        "stock_status"
    ]

    if not all(column in inventory_df.columns for column in required_columns):
        warnings.append(
            "inventory_data.csv: Stock-status validation skipped because "
            "required columns are missing."
        )
        return

    current_stock = get_numeric_series(
        inventory_df,
        "inventory_data.csv",
        "current_stock"
    )

    reorder_level = get_numeric_series(
        inventory_df,
        "inventory_data.csv",
        "reorder_level"
    )

    actual_status = inventory_df["stock_status"].astype(str).str.strip()

    expected_status = np.select(
        [
            current_stock < (reorder_level * 0.80),
            current_stock < reorder_level,
            current_stock > (reorder_level * 3)
        ],
        [
            "Low Stock",
            "Reorder Soon",
            "Overstock"
        ],
        default="Normal"
    )

    mismatch_mask = actual_status != expected_status
    mismatch_count = mismatch_mask.sum()

    if mismatch_count > 0:
        sample_rows = inventory_df.loc[
            mismatch_mask,
            [
                "inventory_id",
                "current_stock",
                "reorder_level",
                "stock_status"
            ]
        ].head(5)

        errors.append(
            "inventory_data.csv: Stock-status logic mismatch found in "
            f"{mismatch_count} rows.\n{sample_rows.to_string(index=False)}"
        )

    if "reorder_required" in inventory_df.columns:
        actual_reorder = inventory_df[
            "reorder_required"
        ].astype(str).str.strip()

        expected_reorder = np.where(
            expected_status == "Low Stock",
            "Yes",
            "No"
        )

        mismatch_mask = actual_reorder != expected_reorder
        mismatch_count = mismatch_mask.sum()

        if mismatch_count > 0:
            errors.append(
                "inventory_data.csv: reorder_required logic mismatch found in "
                f"{mismatch_count} rows."
            )


def check_expiry_dates(inventory_df):
    if inventory_df is None:
        return

    if "expiry_date" not in inventory_df.columns:
        warnings.append(
            "inventory_data.csv: Expiry-date validation skipped because "
            "expiry_date column is missing."
        )
        return

    reference_date_column = None

    for possible_column in [
        "date",
        "inventory_date",
        "record_date",
        "stock_date",
        "last_restock_date"
    ]:
        if possible_column in inventory_df.columns:
            reference_date_column = possible_column
            break

    if reference_date_column is None:
        warnings.append(
            "inventory_data.csv: Expiry-date validation skipped because no "
            "inventory/reference date column was found."
        )
        return

    expiry_date = parse_date_column(
        inventory_df,
        "inventory_data.csv",
        "expiry_date"
    )

    reference_date = parse_date_column(
        inventory_df,
        "inventory_data.csv",
        reference_date_column
    )

    expired_mask = (
        expiry_date.notna()
        & reference_date.notna()
        & (expiry_date < reference_date)
    )

    expired_count = expired_mask.sum()

    if expired_count > 0:
        sample_rows = inventory_df.loc[
            expired_mask,
            [
                "inventory_id",
                reference_date_column,
                "expiry_date"
            ]
        ].head(5)

        errors.append(
            "inventory_data.csv: Expiry date is before record date in "
            f"{expired_count} rows.\n"
            f"{sample_rows.to_string(index=False)}"
        )


def check_finance_calculations(finance_df):
    if finance_df is None:
        return

    required_columns = [
        "total_revenue",
        "total_cost",
        "gross_profit",
        "operating_expense",
        "operating_profit"
    ]

    if not all(column in finance_df.columns for column in required_columns):
        warnings.append(
            "finance_data.csv: Finance-calculation validation skipped because "
            "required columns are missing."
        )
        return

    total_revenue = get_numeric_series(
        finance_df,
        "finance_data.csv",
        "total_revenue"
    )

    total_cost = get_numeric_series(
        finance_df,
        "finance_data.csv",
        "total_cost"
    )

    gross_profit = get_numeric_series(
        finance_df,
        "finance_data.csv",
        "gross_profit"
    )

    operating_expense = get_numeric_series(
        finance_df,
        "finance_data.csv",
        "operating_expense"
    )

    operating_profit = get_numeric_series(
        finance_df,
        "finance_data.csv",
        "operating_profit"
    )

    expected_gross_profit = total_revenue - total_cost

    gross_profit_error = (
        gross_profit - expected_gross_profit
    ).abs() > 1

    if gross_profit_error.sum() > 0:
        errors.append(
            "finance_data.csv: gross_profit calculation mismatch found in "
            f"{gross_profit_error.sum()} rows."
        )

    expected_operating_profit = gross_profit - operating_expense

    operating_profit_error = (
        operating_profit - expected_operating_profit
    ).abs() > 1

    if operating_profit_error.sum() > 0:
        errors.append(
            "finance_data.csv: operating_profit calculation mismatch found in "
            f"{operating_profit_error.sum()} rows."
        )


def check_vendor_delivery_logic(vendor_deliveries_df):
    if vendor_deliveries_df is None:
        return

    required_columns = [
        "order_date",
        "expected_delivery_date",
        "actual_delivery_date",
        "delay_days"
    ]

    if not all(
        column in vendor_deliveries_df.columns
        for column in required_columns
    ):
        warnings.append(
            "vendor_deliveries_data.csv: Delivery-date validation skipped "
            "because required columns are missing."
        )
        return

    order_date = parse_date_column(
        vendor_deliveries_df,
        "vendor_deliveries_data.csv",
        "order_date"
    )

    expected_date = parse_date_column(
        vendor_deliveries_df,
        "vendor_deliveries_data.csv",
        "expected_delivery_date"
    )

    actual_date = parse_date_column(
        vendor_deliveries_df,
        "vendor_deliveries_data.csv",
        "actual_delivery_date"
    )

    delay_days = get_numeric_series(
        vendor_deliveries_df,
        "vendor_deliveries_data.csv",
        "delay_days"
    )

    before_order_mask = (
        actual_date.notna()
        & order_date.notna()
        & (actual_date < order_date)
    )

    if before_order_mask.sum() > 0:
        errors.append(
            "vendor_deliveries_data.csv: Actual delivery date is before "
            f"order date in {before_order_mask.sum()} rows."
        )

    calculated_delay = (actual_date - expected_date).dt.days

    delay_error = (
        calculated_delay.notna()
        & delay_days.notna()
        & ((calculated_delay - delay_days).abs() > 0)
    )

    if delay_error.sum() > 0:
        errors.append(
            "vendor_deliveries_data.csv: delay_days does not match actual "
            f"and expected delivery dates in {delay_error.sum()} rows."
        )


# Load datasets
products = load_dataset("products_data.csv")
stores = load_dataset("stores_data.csv")
vendors = load_dataset("vendors_data.csv")
employees = load_dataset("employees_data.csv")
sales = load_dataset("sales_data.csv")
inventory = load_dataset("inventory_data.csv")
complaints = load_dataset("complaints_data.csv")
finance = load_dataset("finance_data.csv")
vendor_deliveries = load_dataset("vendor_deliveries_data.csv")


# Required column checks
check_required_columns(
    products,
    "products_data.csv",
    ["product_id", "product_name", "vendor_id", "unit_price", "cost_price"]
)

check_required_columns(
    stores,
    "stores_data.csv",
    ["store_id", "store_name", "manager_id", "monthly_sales_target"]
)

check_required_columns(
    vendors,
    "vendors_data.csv",
    ["vendor_id", "vendor_name", "average_delivery_days", "rating"]
)

check_required_columns(
    employees,
    "employees_data.csv",
    ["employee_id", "employee_name", "role", "store_id"]
)

check_required_columns(
    sales,
    "sales_data.csv",
    ["sale_id", "date", "store_id", "product_id", "employee_id", "total_sales"]
)

check_required_columns(
    inventory,
    "inventory_data.csv",
    [
        "inventory_id",
        "date",
        "store_id",
        "product_id",
        "vendor_id",
        "current_stock"
    ]
)

check_required_columns(
    complaints,
    "complaints_data.csv",
    ["complaint_id", "date", "store_id", "product_id", "severity", "status"]
)

check_required_columns(
    finance,
    "finance_data.csv",
    [
        "finance_id",
        "month",
        "store_id",
        "total_revenue",
        "gross_profit",
        "operating_profit",
        "risk_status"
    ]
)

check_required_columns(
    vendor_deliveries,
    "vendor_deliveries_data.csv",
    [
        "purchase_order_id",
        "store_id",
        "vendor_id",
        "product_id",
        "delay_days",
        "delivery_status"
    ]
)


# Duplicate ID checks
check_duplicate_ids(products, "products_data.csv", "product_id")
check_duplicate_ids(stores, "stores_data.csv", "store_id")
check_duplicate_ids(vendors, "vendors_data.csv", "vendor_id")
check_duplicate_ids(employees, "employees_data.csv", "employee_id")
check_duplicate_ids(sales, "sales_data.csv", "sale_id")
check_duplicate_ids(inventory, "inventory_data.csv", "inventory_id")
check_duplicate_ids(complaints, "complaints_data.csv", "complaint_id")
check_duplicate_ids(finance, "finance_data.csv", "finance_id")
check_duplicate_ids(
    vendor_deliveries,
    "vendor_deliveries_data.csv",
    "purchase_order_id"
)


# Missing value checks
check_missing_values(products, "products_data.csv", ["product_id", "vendor_id"])
check_missing_values(stores, "stores_data.csv", ["store_id", "manager_id"])
check_missing_values(vendors, "vendors_data.csv", ["vendor_id"])
check_missing_values(employees, "employees_data.csv", ["employee_id"])
check_missing_values(sales, "sales_data.csv", ["sale_id", "store_id", "product_id"])

check_missing_values(
    inventory,
    "inventory_data.csv",
    ["inventory_id", "date", "store_id", "product_id"]
)

check_missing_values(
    complaints,
    "complaints_data.csv",
    ["complaint_id", "store_id"]
)

check_missing_values(finance, "finance_data.csv", ["finance_id", "store_id"])

check_missing_values(
    vendor_deliveries,
    "vendor_deliveries_data.csv",
    ["purchase_order_id", "store_id", "vendor_id", "product_id"]
)


# Foreign-key checks
check_foreign_key(
    products, "products_data.csv", "vendor_id",
    vendors, "vendors_data.csv", "vendor_id"
)

check_foreign_key(
    stores, "stores_data.csv", "manager_id",
    employees, "employees_data.csv", "employee_id"
)

check_foreign_key(
    sales, "sales_data.csv", "store_id",
    stores, "stores_data.csv", "store_id"
)

check_foreign_key(
    sales, "sales_data.csv", "product_id",
    products, "products_data.csv", "product_id"
)

check_foreign_key(
    sales, "sales_data.csv", "employee_id",
    employees, "employees_data.csv", "employee_id"
)

check_foreign_key(
    inventory, "inventory_data.csv", "store_id",
    stores, "stores_data.csv", "store_id"
)

check_foreign_key(
    inventory, "inventory_data.csv", "product_id",
    products, "products_data.csv", "product_id"
)

check_foreign_key(
    inventory, "inventory_data.csv", "vendor_id",
    vendors, "vendors_data.csv", "vendor_id"
)

check_foreign_key(
    complaints, "complaints_data.csv", "store_id",
    stores, "stores_data.csv", "store_id"
)

check_foreign_key(
    complaints, "complaints_data.csv", "product_id",
    products, "products_data.csv", "product_id"
)

check_foreign_key(
    finance, "finance_data.csv", "store_id",
    stores, "stores_data.csv", "store_id"
)

check_foreign_key(
    vendor_deliveries, "vendor_deliveries_data.csv", "store_id",
    stores, "stores_data.csv", "store_id"
)

check_foreign_key(
    vendor_deliveries, "vendor_deliveries_data.csv", "vendor_id",
    vendors, "vendors_data.csv", "vendor_id"
)

check_foreign_key(
    vendor_deliveries, "vendor_deliveries_data.csv", "product_id",
    products, "products_data.csv", "product_id"
)


# Numeric data checks
check_non_negative(
    products,
    "products_data.csv",
    ["unit_price", "cost_price", "margin_percent", "reorder_level"]
)

check_non_negative(
    stores,
    "stores_data.csv",
    ["monthly_sales_target"]
)

check_non_negative(
    vendors,
    "vendors_data.csv",
    ["average_delivery_days", "rating"]
)

check_non_negative(
    sales,
    "sales_data.csv",
    [
        "quantity_sold",
        "unit_price",
        "discount_percent",
        "total_sales",
        "total_cost"
    ]
)

check_non_negative(
    inventory,
    "inventory_data.csv",
    ["current_stock", "reorder_level"]
)

check_non_negative(
    finance,
    "finance_data.csv",
    [
        "monthly_sales_target",
        "total_revenue",
        "total_cost",
        "gross_profit",
        "operating_expense"
    ]
)

check_non_negative(
    vendor_deliveries,
    "vendor_deliveries_data.csv",
    [
        "ordered_quantity",
        "received_quantity",
        "unit_cost",
        "purchase_value",
        "delay_days",
        "quality_rating"
    ]
)


# Date validation
parse_date_column(stores, "stores_data.csv", "opening_date")
parse_date_column(sales, "sales_data.csv", "date")
parse_date_column(inventory, "inventory_data.csv", "date")
parse_date_column(complaints, "complaints_data.csv", "date")

parse_date_column(
    vendor_deliveries,
    "vendor_deliveries_data.csv",
    "order_date"
)

parse_date_column(
    vendor_deliveries,
    "vendor_deliveries_data.csv",
    "expected_delivery_date"
)

parse_date_column(
    vendor_deliveries,
    "vendor_deliveries_data.csv",
    "actual_delivery_date"
)


# Business logic validation
check_inventory_status_logic(inventory)
check_expiry_dates(inventory)
check_finance_calculations(finance)
check_vendor_delivery_logic(vendor_deliveries)


# Create report
report_lines = []

report_lines.append("DATA VALIDATION REPORT")
report_lines.append("=" * 50)
report_lines.append("")

report_lines.append("DATASET SUMMARY")
report_lines.extend(summary)
report_lines.append("")

report_lines.append("ERRORS")
if errors:
    report_lines.extend(errors)
else:
    report_lines.append("No validation errors found.")

report_lines.append("")

report_lines.append("WARNINGS")
if warnings:
    report_lines.extend(warnings)
else:
    report_lines.append("No warnings found.")

report_text = "\n".join(report_lines)

report_path = REPORT_DIR / "data_validation_report.txt"

with open(report_path, "w", encoding="utf-8") as file:
    file.write(report_text)

print(report_text)
print("\nValidation report saved at:")
print(report_path)