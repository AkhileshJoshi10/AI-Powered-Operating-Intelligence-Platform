import pandas as pd
import numpy as np
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "reports"

DATE_FORMAT = "%Y-%m-%d"

GENERIC_MISSING_TEXT_VALUES = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "nan",
}

REPORT_DIR.mkdir(exist_ok=True)

errors = []
warnings = []
summary = []


def get_generic_missing_mask(series):
    values = series.astype("string").str.strip()

    return (
        values.isna()
        | values.str.lower()
        .isin(GENERIC_MISSING_TEXT_VALUES)
        .fillna(False)
    )


def load_dataset(filename):
    file_path = DATA_DIR / filename

    if not file_path.exists():
        warnings.append(f"File not found (skipped): {filename}")
        return None

    df = pd.read_csv(
        file_path,
        dtype="string",
        keep_default_na=False,
    )

    summary.append(
        f"{filename}: {len(df)} rows, {len(df.columns)} columns"
    )

    return df


def check_required_columns(df, dataset_name, required_columns):
    if df is None:
        return

    missing_columns = [
        column
        for column in required_columns
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
            f"{dataset_name}: {duplicate_count} duplicate values found "
            f"in {id_column}"
        )


def check_missing_values(df, dataset_name, required_columns):
    if df is None:
        return

    for column in required_columns:
        if column not in df.columns:
            continue

        missing_count = get_generic_missing_mask(df[column]).sum()

        if missing_count > 0:
            errors.append(
                f"{dataset_name}: {missing_count} missing values found "
                f"in {column}"
            )


def check_foreign_key(
    child_df,
    child_name,
    child_column,
    parent_df,
    parent_name,
    parent_column,
):
    if child_df is None or parent_df is None:
        return

    if child_column not in child_df.columns:
        warnings.append(
            f"{child_name}: Relationship column not found -> "
            f"{child_column}"
        )
        return

    if parent_column not in parent_df.columns:
        warnings.append(
            f"{parent_name}: Relationship column not found -> "
            f"{parent_column}"
        )
        return

    child_values = child_df[child_column].astype("string").str.strip()
    parent_values = parent_df[parent_column].astype("string").str.strip()

    missing_mask = get_generic_missing_mask(child_values)

    invalid_values = child_values[
        ~missing_mask
        & ~child_values.isin(parent_values)
    ].unique()

    if len(invalid_values) > 0:
        errors.append(
            f"{child_name}: Invalid {child_column} values not found in "
            f"{parent_name} -> {list(invalid_values[:10])}"
        )


def get_numeric_series(df, dataset_name, column):
    if df is None or column not in df.columns:
        return None

    raw_values = df[column].astype("string")
    missing_mask = get_generic_missing_mask(raw_values)

    numeric_values = pd.to_numeric(
        raw_values.mask(missing_mask, pd.NA),
        errors="coerce",
    )

    invalid_mask = (
        ~missing_mask
        & numeric_values.isna()
    )

    if invalid_mask.sum() > 0:
        invalid_values = raw_values[
            invalid_mask
        ].head(5).tolist()

        errors.append(
            f"{dataset_name}: Non-numeric values found in "
            f"{column} -> {invalid_values}"
        )

    return numeric_values


def check_non_negative(df, dataset_name, columns):
    if df is None:
        return

    for column in columns:
        if column not in df.columns:
            continue

        numeric_values = get_numeric_series(
            df,
            dataset_name,
            column,
        )

        if numeric_values is None:
            continue

        negative_count = (numeric_values < 0).sum()

        if negative_count > 0:
            errors.append(
                f"{dataset_name}: {negative_count} negative values "
                f"found in {column}"
            )


def parse_date_column(
    df,
    dataset_name,
    column,
    required=False,
):
    if df is None or column not in df.columns:
        return None

    raw_values = df[column].astype("string")
    missing_mask = get_generic_missing_mask(raw_values)

    if required and missing_mask.sum() > 0:
        errors.append(
            f"{dataset_name}: {missing_mask.sum()} missing values "
            f"found in required date column {column}"
        )

    parsed_dates = pd.to_datetime(
        raw_values.mask(missing_mask, pd.NA),
        format=DATE_FORMAT,
        errors="coerce",
    )

    invalid_mask = (
        ~missing_mask
        & parsed_dates.isna()
    )

    if invalid_mask.sum() > 0:
        invalid_values = raw_values[
            invalid_mask
        ].head(5).tolist()

        errors.append(
            f"{dataset_name}: Invalid date values found in "
            f"{column} -> {invalid_values}"
        )

    return parsed_dates


def parse_month_column(df, dataset_name, column):
    if df is None or column not in df.columns:
        return None

    raw_values = df[column].astype("string")
    missing_mask = get_generic_missing_mask(raw_values)

    if missing_mask.sum() > 0:
        errors.append(
            f"{dataset_name}: {missing_mask.sum()} missing values "
            f"found in required month column {column}"
        )

    parsed_months = pd.to_datetime(
        raw_values.mask(missing_mask, pd.NA),
        format="%Y-%m",
        errors="coerce",
    )

    invalid_mask = (
        ~missing_mask
        & parsed_months.isna()
    )

    if invalid_mask.sum() > 0:
        invalid_values = raw_values[
            invalid_mask
        ].head(5).tolist()

        errors.append(
            f"{dataset_name}: Invalid month values found in "
            f"{column} -> {invalid_values}"
        )

    return parsed_months


def check_products_perishability_logic(products_df):
    if products_df is None:
        return

    required_columns = [
        "product_id",
        "is_perishable",
        "shelf_life_days",
    ]

    if not all(
        column in products_df.columns
        for column in required_columns
    ):
        warnings.append(
            "products_cleaned.csv: Perishability validation skipped "
            "because required columns are missing."
        )
        return

    is_perishable = products_df[
        "is_perishable"
    ].astype("string").str.strip()

    invalid_flags = is_perishable[
        ~is_perishable.isin(["Yes", "No"])
    ].dropna().unique()

    if len(invalid_flags) > 0:
        errors.append(
            "products_cleaned.csv: Invalid is_perishable values -> "
            f"{list(invalid_flags[:10])}"
        )

    shelf_life = products_df[
        "shelf_life_days"
    ].astype("string").str.strip()

    perishable_mask = is_perishable == "Yes"
    non_perishable_mask = is_perishable == "No"

    missing_shelf_life_mask = get_generic_missing_mask(shelf_life)

    missing_perishable_count = (
        perishable_mask
        & missing_shelf_life_mask
    ).sum()

    if missing_perishable_count > 0:
        errors.append(
            "products_cleaned.csv: Missing shelf_life_days for "
            f"{missing_perishable_count} perishable products."
        )

    shelf_life_numeric = pd.to_numeric(
        shelf_life.mask(missing_shelf_life_mask, pd.NA),
        errors="coerce",
    )

    invalid_perishable_mask = (
        perishable_mask
        & ~missing_shelf_life_mask
        & shelf_life_numeric.isna()
    )

    if invalid_perishable_mask.sum() > 0:
        invalid_values = shelf_life[
            invalid_perishable_mask
        ].head(5).tolist()

        errors.append(
            "products_cleaned.csv: Invalid shelf_life_days for "
            f"perishable products -> {invalid_values}"
        )

    non_integer_mask = (
        perishable_mask
        & shelf_life_numeric.notna()
        & ((shelf_life_numeric % 1) != 0)
    )

    if non_integer_mask.sum() > 0:
        errors.append(
            "products_cleaned.csv: shelf_life_days must contain "
            "whole numbers for perishable products."
        )

    invalid_shelf_life_mask = (
        perishable_mask
        & shelf_life_numeric.notna()
        & (shelf_life_numeric <= 0)
    )

    if invalid_shelf_life_mask.sum() > 0:
        errors.append(
            "products_cleaned.csv: shelf_life_days must be greater "
            "than zero for perishable products."
        )

    invalid_non_perishable_mask = (
        non_perishable_mask
        & (shelf_life.str.upper() != "NA")
    )

    if invalid_non_perishable_mask.sum() > 0:
        invalid_values = shelf_life[
            invalid_non_perishable_mask
        ].head(5).tolist()

        errors.append(
            "products_cleaned.csv: Non-perishable products must have "
            f"shelf_life_days as NA -> {invalid_values}"
        )


def check_inventory_status_logic(inventory_df):
    if inventory_df is None:
        return

    required_columns = [
        "inventory_id",
        "current_stock",
        "reorder_level",
        "stock_status",
    ]

    if not all(
        column in inventory_df.columns
        for column in required_columns
    ):
        warnings.append(
            "inventory_cleaned.csv: Stock-status validation skipped "
            "because required columns are missing."
        )
        return

    current_stock = get_numeric_series(
        inventory_df,
        "inventory_cleaned.csv",
        "current_stock",
    )

    reorder_level = get_numeric_series(
        inventory_df,
        "inventory_cleaned.csv",
        "reorder_level",
    )

    actual_status = inventory_df[
        "stock_status"
    ].astype("string").str.strip()

    expected_status = np.select(
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
    )

    mismatch_mask = actual_status != expected_status

    if mismatch_mask.sum() > 0:
        sample_rows = inventory_df.loc[
            mismatch_mask,
            [
                "inventory_id",
                "current_stock",
                "reorder_level",
                "stock_status",
            ],
        ].head(5)

        errors.append(
            "inventory_cleaned.csv: Stock-status logic mismatch "
            f"found in {mismatch_mask.sum()} rows.\n"
            f"{sample_rows.to_string(index=False)}"
        )

    if "reorder_required" in inventory_df.columns:
        actual_reorder = inventory_df[
            "reorder_required"
        ].astype("string").str.strip()

        expected_reorder = np.where(
            expected_status == "Low Stock",
            "Yes",
            "No",
        )

        mismatch_mask = actual_reorder != expected_reorder

        if mismatch_mask.sum() > 0:
            errors.append(
                "inventory_cleaned.csv: reorder_required logic "
                f"mismatch found in {mismatch_mask.sum()} rows."
            )


def check_inventory_expiry_logic(inventory_df, products_df):
    if inventory_df is None or products_df is None:
        return

    required_inventory_columns = [
        "inventory_id",
        "date",
        "product_id",
        "expiry_date",
    ]

    required_product_columns = [
        "product_id",
        "is_perishable",
    ]

    if not all(
        column in inventory_df.columns
        for column in required_inventory_columns
    ):
        warnings.append(
            "inventory_cleaned.csv: Expiry-date validation skipped "
            "because required inventory columns are missing."
        )
        return

    if not all(
        column in products_df.columns
        for column in required_product_columns
    ):
        warnings.append(
            "inventory_cleaned.csv: Expiry-date validation skipped "
            "because product perishability information is missing."
        )
        return

    product_perishability_map = products_df.set_index(
        "product_id"
    )["is_perishable"].to_dict()

    product_id = inventory_df["product_id"].astype("string").str.strip()

    is_perishable = product_id.map(product_perishability_map)

    missing_product_mapping_mask = (
        ~get_generic_missing_mask(product_id)
        & is_perishable.isna()
    )

    if missing_product_mapping_mask.sum() > 0:
        invalid_product_ids = product_id[
            missing_product_mapping_mask
        ].unique()

        errors.append(
            "inventory_cleaned.csv: Product IDs missing from "
            f"products_cleaned.csv -> {list(invalid_product_ids[:10])}"
        )

    inventory_date = parse_date_column(
        inventory_df,
        "inventory_cleaned.csv",
        "date",
        required=True,
    )

    expiry_text = inventory_df[
        "expiry_date"
    ].astype("string").str.strip()

    expiry_missing_mask = get_generic_missing_mask(expiry_text)

    expiry_date = pd.to_datetime(
        expiry_text.mask(expiry_missing_mask, pd.NA),
        format=DATE_FORMAT,
        errors="coerce",
    )

    perishable_mask = is_perishable == "Yes"
    non_perishable_mask = is_perishable == "No"

    missing_perishable_expiry_count = (
        perishable_mask
        & expiry_missing_mask
    ).sum()

    if missing_perishable_expiry_count > 0:
        errors.append(
            "inventory_cleaned.csv: Missing expiry_date for "
            f"{missing_perishable_expiry_count} perishable inventory rows."
        )

    invalid_perishable_expiry_mask = (
        perishable_mask
        & ~expiry_missing_mask
        & expiry_date.isna()
    )

    if invalid_perishable_expiry_mask.sum() > 0:
        invalid_values = expiry_text[
            invalid_perishable_expiry_mask
        ].head(5).tolist()

        errors.append(
            "inventory_cleaned.csv: Invalid expiry_date values for "
            f"perishable inventory -> {invalid_values}"
        )

    invalid_non_perishable_expiry_mask = (
        non_perishable_mask
        & (expiry_text.str.upper() != "NA")
    )

    if invalid_non_perishable_expiry_mask.sum() > 0:
        invalid_values = expiry_text[
            invalid_non_perishable_expiry_mask
        ].head(5).tolist()

        errors.append(
            "inventory_cleaned.csv: Non-perishable inventory must have "
            f"expiry_date as NA -> {invalid_values}"
        )

    expired_mask = (
        perishable_mask
        & expiry_date.notna()
        & inventory_date.notna()
        & (expiry_date < inventory_date)
    )

    if expired_mask.sum() > 0:
        sample_rows = inventory_df.loc[
            expired_mask,
            [
                "inventory_id",
                "date",
                "expiry_date",
            ],
        ].head(5)

        errors.append(
            "inventory_cleaned.csv: Expiry date is before inventory "
            f"record date in {expired_mask.sum()} rows.\n"
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
        "operating_profit",
    ]

    if not all(
        column in finance_df.columns
        for column in required_columns
    ):
        warnings.append(
            "finance_cleaned.csv: Finance-calculation validation "
            "skipped because required columns are missing."
        )
        return

    total_revenue = get_numeric_series(
        finance_df,
        "finance_cleaned.csv",
        "total_revenue",
    )

    total_cost = get_numeric_series(
        finance_df,
        "finance_cleaned.csv",
        "total_cost",
    )

    gross_profit = get_numeric_series(
        finance_df,
        "finance_cleaned.csv",
        "gross_profit",
    )

    operating_expense = get_numeric_series(
        finance_df,
        "finance_cleaned.csv",
        "operating_expense",
    )

    operating_profit = get_numeric_series(
        finance_df,
        "finance_cleaned.csv",
        "operating_profit",
    )

    expected_gross_profit = total_revenue - total_cost

    gross_profit_error = (
        gross_profit - expected_gross_profit
    ).abs() > 1

    if gross_profit_error.sum() > 0:
        errors.append(
            "finance_cleaned.csv: gross_profit calculation mismatch "
            f"found in {gross_profit_error.sum()} rows."
        )

    expected_operating_profit = gross_profit - operating_expense

    operating_profit_error = (
        operating_profit - expected_operating_profit
    ).abs() > 1

    if operating_profit_error.sum() > 0:
        errors.append(
            "finance_cleaned.csv: operating_profit calculation "
            f"mismatch found in {operating_profit_error.sum()} rows."
        )


def check_vendor_delivery_logic(vendor_deliveries_df):
    if vendor_deliveries_df is None:
        return

    required_columns = [
        "purchase_order_id",
        "order_date",
        "expected_delivery_date",
        "actual_delivery_date",
        "delay_days",
    ]

    if not all(
        column in vendor_deliveries_df.columns
        for column in required_columns
    ):
        warnings.append(
            "vendor_deliveries_cleaned.csv: Delivery-date validation "
            "skipped because required columns are missing."
        )
        return

    order_date = parse_date_column(
        vendor_deliveries_df,
        "vendor_deliveries_cleaned.csv",
        "order_date",
        required=True,
    )

    expected_delivery_date = parse_date_column(
        vendor_deliveries_df,
        "vendor_deliveries_cleaned.csv",
        "expected_delivery_date",
        required=True,
    )

    actual_delivery_date = parse_date_column(
        vendor_deliveries_df,
        "vendor_deliveries_cleaned.csv",
        "actual_delivery_date",
        required=True,
    )

    delay_days = get_numeric_series(
        vendor_deliveries_df,
        "vendor_deliveries_cleaned.csv",
        "delay_days",
    )

    before_order_mask = (
        actual_delivery_date.notna()
        & order_date.notna()
        & (actual_delivery_date < order_date)
    )

    if before_order_mask.sum() > 0:
        errors.append(
            "vendor_deliveries_cleaned.csv: Actual delivery date is "
            f"before order date in {before_order_mask.sum()} rows."
        )

    calculated_delay = (
        actual_delivery_date - expected_delivery_date
    ).dt.days

    delay_error = (
        calculated_delay.notna()
        & delay_days.notna()
        & ((calculated_delay - delay_days).abs() > 0)
    )

    if delay_error.sum() > 0:
        errors.append(
            "vendor_deliveries_cleaned.csv: delay_days does not match "
            "actual and expected delivery dates in "
            f"{delay_error.sum()} rows."
        )


products = load_dataset("products_cleaned.csv")
stores = load_dataset("stores_cleaned.csv")
vendors = load_dataset("vendors_cleaned.csv")
employees = load_dataset("employees_cleaned.csv")
sales = load_dataset("sales_cleaned.csv")
inventory = load_dataset("inventory_cleaned.csv")
complaints = load_dataset("complaints_cleaned.csv")
finance = load_dataset("finance_cleaned.csv")
vendor_deliveries = load_dataset("vendor_deliveries_cleaned.csv")


check_required_columns(
    products,
    "products_cleaned.csv",
    [
        "product_id",
        "product_name",
        "vendor_id",
        "unit_price",
        "cost_price",
        "is_perishable",
        "shelf_life_days",
    ],
)

check_required_columns(
    stores,
    "stores_cleaned.csv",
    [
        "store_id",
        "store_name",
        "manager_id",
        "opening_date",
        "monthly_sales_target",
    ],
)

check_required_columns(
    vendors,
    "vendors_cleaned.csv",
    [
        "vendor_id",
        "vendor_name",
        "average_delivery_days",
        "rating",
    ],
)

check_required_columns(
    employees,
    "employees_cleaned.csv",
    [
        "employee_id",
        "employee_name",
        "role",
        "store_id",
    ],
)

check_required_columns(
    sales,
    "sales_cleaned.csv",
    [
        "sale_id",
        "date",
        "store_id",
        "product_id",
        "employee_id",
        "total_sales",
    ],
)

check_required_columns(
    inventory,
    "inventory_cleaned.csv",
    [
        "inventory_id",
        "date",
        "store_id",
        "product_id",
        "vendor_id",
        "current_stock",
        "reorder_level",
        "stock_status",
        "reorder_required",
        "expiry_date",
    ],
)

check_required_columns(
    complaints,
    "complaints_cleaned.csv",
    [
        "complaint_id",
        "date",
        "store_id",
        "product_id",
        "severity",
        "status",
    ],
)

check_required_columns(
    finance,
    "finance_cleaned.csv",
    [
        "finance_id",
        "month",
        "store_id",
        "total_revenue",
        "gross_profit",
        "operating_profit",
        "risk_status",
    ],
)

check_required_columns(
    vendor_deliveries,
    "vendor_deliveries_cleaned.csv",
    [
        "purchase_order_id",
        "order_date",
        "expected_delivery_date",
        "actual_delivery_date",
        "store_id",
        "vendor_id",
        "product_id",
        "delay_days",
        "delivery_status",
    ],
)


check_duplicate_ids(products, "products_cleaned.csv", "product_id")
check_duplicate_ids(stores, "stores_cleaned.csv", "store_id")
check_duplicate_ids(vendors, "vendors_cleaned.csv", "vendor_id")
check_duplicate_ids(employees, "employees_cleaned.csv", "employee_id")
check_duplicate_ids(sales, "sales_cleaned.csv", "sale_id")
check_duplicate_ids(inventory, "inventory_cleaned.csv", "inventory_id")
check_duplicate_ids(complaints, "complaints_cleaned.csv", "complaint_id")
check_duplicate_ids(finance, "finance_cleaned.csv", "finance_id")

check_duplicate_ids(
    vendor_deliveries,
    "vendor_deliveries_cleaned.csv",
    "purchase_order_id",
)


check_missing_values(
    products,
    "products_cleaned.csv",
    [
        "product_id",
        "product_name",
        "vendor_id",
        "unit_price",
        "cost_price",
        "is_perishable",
    ],
)

check_missing_values(
    stores,
    "stores_cleaned.csv",
    [
        "store_id",
        "store_name",
        "manager_id",
        "opening_date",
        "monthly_sales_target",
    ],
)

check_missing_values(
    vendors,
    "vendors_cleaned.csv",
    [
        "vendor_id",
        "vendor_name",
        "average_delivery_days",
        "rating",
    ],
)

check_missing_values(
    employees,
    "employees_cleaned.csv",
    [
        "employee_id",
        "employee_name",
        "role",
        "store_id",
    ],
)

check_missing_values(
    sales,
    "sales_cleaned.csv",
    [
        "sale_id",
        "date",
        "store_id",
        "product_id",
        "employee_id",
        "total_sales",
    ],
)

check_missing_values(
    inventory,
    "inventory_cleaned.csv",
    [
        "inventory_id",
        "date",
        "store_id",
        "product_id",
        "vendor_id",
        "current_stock",
        "reorder_level",
        "stock_status",
        "reorder_required",
    ],
)

check_missing_values(
    complaints,
    "complaints_cleaned.csv",
    [
        "complaint_id",
        "date",
        "store_id",
        "product_id",
        "severity",
        "status",
    ],
)

check_missing_values(
    finance,
    "finance_cleaned.csv",
    [
        "finance_id",
        "month",
        "store_id",
        "total_revenue",
        "total_cost",
        "gross_profit",
        "operating_expense",
        "operating_profit",
        "target_achievement_percent",
        "risk_status",
    ],
)

check_missing_values(
    vendor_deliveries,
    "vendor_deliveries_cleaned.csv",
    [
        "purchase_order_id",
        "order_date",
        "expected_delivery_date",
        "actual_delivery_date",
        "store_id",
        "vendor_id",
        "product_id",
        "ordered_quantity",
        "received_quantity",
        "delay_days",
        "delivery_status",
        "quality_rating",
    ],
)


check_foreign_key(
    products,
    "products_cleaned.csv",
    "vendor_id",
    vendors,
    "vendors_cleaned.csv",
    "vendor_id",
)

check_foreign_key(
    stores,
    "stores_cleaned.csv",
    "manager_id",
    employees,
    "employees_cleaned.csv",
    "employee_id",
)

check_foreign_key(
    sales,
    "sales_cleaned.csv",
    "store_id",
    stores,
    "stores_cleaned.csv",
    "store_id",
)

check_foreign_key(
    sales,
    "sales_cleaned.csv",
    "product_id",
    products,
    "products_cleaned.csv",
    "product_id",
)

check_foreign_key(
    sales,
    "sales_cleaned.csv",
    "employee_id",
    employees,
    "employees_cleaned.csv",
    "employee_id",
)

check_foreign_key(
    inventory,
    "inventory_cleaned.csv",
    "store_id",
    stores,
    "stores_cleaned.csv",
    "store_id",
)

check_foreign_key(
    inventory,
    "inventory_cleaned.csv",
    "product_id",
    products,
    "products_cleaned.csv",
    "product_id",
)

check_foreign_key(
    inventory,
    "inventory_cleaned.csv",
    "vendor_id",
    vendors,
    "vendors_cleaned.csv",
    "vendor_id",
)

check_foreign_key(
    complaints,
    "complaints_cleaned.csv",
    "store_id",
    stores,
    "stores_cleaned.csv",
    "store_id",
)

check_foreign_key(
    complaints,
    "complaints_cleaned.csv",
    "product_id",
    products,
    "products_cleaned.csv",
    "product_id",
)

check_foreign_key(
    finance,
    "finance_cleaned.csv",
    "store_id",
    stores,
    "stores_cleaned.csv",
    "store_id",
)

check_foreign_key(
    vendor_deliveries,
    "vendor_deliveries_cleaned.csv",
    "store_id",
    stores,
    "stores_cleaned.csv",
    "store_id",
)

check_foreign_key(
    vendor_deliveries,
    "vendor_deliveries_cleaned.csv",
    "vendor_id",
    vendors,
    "vendors_cleaned.csv",
    "vendor_id",
)

check_foreign_key(
    vendor_deliveries,
    "vendor_deliveries_cleaned.csv",
    "product_id",
    products,
    "products_cleaned.csv",
    "product_id",
)


check_non_negative(
    products,
    "products_cleaned.csv",
    [
        "unit_price",
        "cost_price",
        "margin_percent",
        "reorder_level",
    ],
)

check_non_negative(
    stores,
    "stores_cleaned.csv",
    [
        "monthly_sales_target",
    ],
)

check_non_negative(
    vendors,
    "vendors_cleaned.csv",
    [
        "average_delivery_days",
        "rating",
    ],
)

check_non_negative(
    employees,
    "employees_cleaned.csv",
    [
        "monthly_target",
    ],
)

check_non_negative(
    sales,
    "sales_cleaned.csv",
    [
        "quantity_sold",
        "unit_price",
        "discount_percent",
        "total_sales",
        "total_cost",
    ],
)

check_non_negative(
    inventory,
    "inventory_cleaned.csv",
    [
        "current_stock",
        "reorder_level",
        "days_to_expiry",
    ],
)

check_non_negative(
    finance,
    "finance_cleaned.csv",
    [
        "monthly_sales_target",
        "total_revenue",
        "total_cost",
        "gross_profit",
        "operating_expense",
        "target_achievement_percent",
    ],
)

check_non_negative(
    vendor_deliveries,
    "vendor_deliveries_cleaned.csv",
    [
        "ordered_quantity",
        "received_quantity",
        "unit_cost",
        "purchase_value",
        "delay_days",
        "quality_rating",
    ],
)


parse_date_column(
    stores,
    "stores_cleaned.csv",
    "opening_date",
    required=True,
)

parse_date_column(
    sales,
    "sales_cleaned.csv",
    "date",
    required=True,
)

parse_date_column(
    complaints,
    "complaints_cleaned.csv",
    "date",
    required=True,
)

parse_month_column(
    finance,
    "finance_cleaned.csv",
    "month",
)


check_products_perishability_logic(products)
check_inventory_status_logic(inventory)
check_inventory_expiry_logic(inventory, products)
check_finance_calculations(finance)
check_vendor_delivery_logic(vendor_deliveries)


report_lines = [
    "PROCESSED DATA VALIDATION REPORT",
    "=" * 60,
    "",
    "DATASET SUMMARY",
]

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

report_path = REPORT_DIR / "processed_data_validation_report.txt"

report_path.write_text(
    report_text,
    encoding="utf-8",
)

print(report_text)
print("\nProcessed-data validation report saved at:")
print(report_path)