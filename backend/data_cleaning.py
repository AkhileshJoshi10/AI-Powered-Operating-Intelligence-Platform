import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "reports"

DATE_FORMAT = "%d-%m-%y"

GENERIC_MISSING_TEXT_VALUES = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "nan",
}

PROCESSED_DATA_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

cleaning_logs = []


CATEGORICAL_LABEL_MAPS = {
    "is_perishable": {
        "yes": "Yes",
        "no": "No",
    },
    "region": {
        "north": "North",
        "south": "South",
        "east": "East",
        "west": "West",
        "central": "Central",
    },
    "department": {
        "sales": "Sales",
        "inventory": "Inventory",
        "finance": "Finance",
        "procurement": "Procurement",
        "customer support": "Customer Support",
    },
    "severity": {
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    },
    "status": {
        "open": "Open",
        "in progress": "In Progress",
        "resolved": "Resolved",
        "closed": "Closed",
    },
    "stock_status": {
        "low stock": "Low Stock",
        "reorder soon": "Reorder Soon",
        "overstock": "Overstock",
        "normal": "Normal",
    },
    "reorder_required": {
        "yes": "Yes",
        "no": "No",
    },
    "risk_status": {
        "high risk": "High Risk",
        "medium risk": "Medium Risk",
        "low risk": "Low Risk",
    },
    "delivery_status": {
        "delayed and partial": "Delayed and Partial",
        "delayed": "Delayed",
        "partial delivery": "Partial Delivery",
        "delivered on time": "Delivered On Time",
    },
    "supply_status": {
        "active": "Active",
        "delayed": "Delayed",
        "inactive": "Inactive",
    },
    "operational_status": {
        "active": "Active",
        "inactive": "Inactive",
    },
    "employment_status": {
        "active": "Active",
        "inactive": "Inactive",
    },
    "payment_status": {
        "paid": "Paid",
        "pending": "Pending",
        "delayed": "Delayed",
    },
}


DATASETS = {
    "products_data.csv": {
        "output": "products_cleaned.csv",
        "date_columns": [],
        "month_columns": [],
        "numeric_columns": [
            "unit_price",
            "cost_price",
            "margin_percent",
            "reorder_level",
        ],
        "integer_columns": [
            "reorder_level",
        ],
        "categorical_columns": [
            "category",
            "sub_category",
            "is_perishable",
        ],
        "drop_columns": [],
    },
    "stores_data.csv": {
        "output": "stores_cleaned.csv",
        "date_columns": [
            "opening_date",
        ],
        "month_columns": [],
        "numeric_columns": [
            "monthly_sales_target",
        ],
        "integer_columns": [],
        "categorical_columns": [
            "region",
            "operational_status",
        ],
        "drop_columns": [],
    },
    "vendors_data.csv": {
        "output": "vendors_cleaned.csv",
        "date_columns": [],
        "month_columns": [],
        "numeric_columns": [
            "average_delivery_days",
            "rating",
        ],
        "integer_columns": [
            "average_delivery_days",
        ],
        "categorical_columns": [
            "region",
            "supply_status",
        ],
        "drop_columns": [],
    },
    "employees_data.csv": {
        "output": "employees_cleaned.csv",
        "date_columns": [],
        "month_columns": [],
        "numeric_columns": [
            "monthly_target",
        ],
        "integer_columns": [],
        "categorical_columns": [
            "department",
            "region",
            "employment_status",
        ],
        "drop_columns": [],
    },
    "sales_data.csv": {
        "output": "sales_cleaned.csv",
        "date_columns": [
            "date",
        ],
        "month_columns": [],
        "numeric_columns": [
            "quantity_sold",
            "unit_price",
            "discount_percent",
            "total_sales",
            "total_cost",
            "profit",
        ],
        "integer_columns": [
            "quantity_sold",
        ],
        "categorical_columns": [
            "region",
            "payment_status",
        ],
        "drop_columns": [],
    },
    "inventory_data.csv": {
        "output": "inventory_cleaned.csv",
        "date_columns": [
            "date",
        ],
        "month_columns": [],
        "numeric_columns": [
            "current_stock",
            "reorder_level",
            "days_to_expiry",
        ],
        "integer_columns": [
            "current_stock",
            "reorder_level",
            "days_to_expiry",
        ],
        "categorical_columns": [
            "stock_status",
            "reorder_required",
        ],
        "drop_columns": [
            "reorder_trigger_level",
        ],
    },
    "complaints_data.csv": {
        "output": "complaints_cleaned.csv",
        "date_columns": [
            "date",
        ],
        "month_columns": [],
        "numeric_columns": [
            "resolution_time_days",
        ],
        "integer_columns": [
            "resolution_time_days",
        ],
        "categorical_columns": [
            "severity",
            "status",
        ],
        "drop_columns": [],
    },
    "finance_data.csv": {
        "output": "finance_cleaned.csv",
        "date_columns": [],
        "month_columns": [
            "month",
        ],
        "numeric_columns": [
            "monthly_sales_target",
            "total_revenue",
            "total_cost",
            "gross_profit",
            "operating_expense",
            "operating_profit",
            "target_achievement_percent",
        ],
        "integer_columns": [],
        "categorical_columns": [
            "region",
            "risk_status",
        ],
        "drop_columns": [],
    },
    "vendor_deliveries_data.csv": {
        "output": "vendor_deliveries_cleaned.csv",
        "date_columns": [
            "order_date",
            "expected_delivery_date",
            "actual_delivery_date",
        ],
        "month_columns": [],
        "numeric_columns": [
            "ordered_quantity",
            "received_quantity",
            "unit_cost",
            "purchase_value",
            "delay_days",
            "quality_rating",
        ],
        "integer_columns": [
            "ordered_quantity",
            "received_quantity",
            "delay_days",
        ],
        "categorical_columns": [
            "delivery_status",
        ],
        "drop_columns": [],
    },
}


PROCESSING_ORDER = [
    "products_data.csv",
    "stores_data.csv",
    "vendors_data.csv",
    "employees_data.csv",
    "sales_data.csv",
    "inventory_data.csv",
    "complaints_data.csv",
    "finance_data.csv",
    "vendor_deliveries_data.csv",
]


def get_generic_missing_mask(series):
    values = series.astype("string").str.strip()

    return (
        values.isna()
        | values.str.lower()
        .isin(GENERIC_MISSING_TEXT_VALUES)
        .fillna(False)
    )


def normalize_text_columns(df, stats):
    for column in df.columns:
        original = df[column].astype("string")

        cleaned = (
            original
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

        changed_mask = (
            original.notna()
            & (original != cleaned).fillna(False)
        )

        df[column] = cleaned
        stats["text_values_normalized"] += int(changed_mask.sum())

    return df


def standardize_id_columns(df, stats):
    id_columns = [
        column
        for column in df.columns
        if column == "id" or column.endswith("_id")
    ]

    for column in id_columns:
        original = df[column].astype("string")
        missing_mask = get_generic_missing_mask(original)

        standardized = (
            original
            .str.strip()
            .str.upper()
            .mask(missing_mask, pd.NA)
        )

        changed_mask = (
            original.notna()
            & (original != standardized).fillna(False)
        )

        df[column] = standardized
        stats["id_values_standardized"] += int(changed_mask.sum())

    return df


def standardize_categorical_columns(df, config, stats):
    for column in config["categorical_columns"]:
        if column not in df.columns:
            continue

        original = df[column].astype("string")
        missing_mask = get_generic_missing_mask(original)

        normalized_key = (
            original
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.lower()
        )

        mapped_values = normalized_key.map(
            CATEGORICAL_LABEL_MAPS.get(column, {})
        )

        standardized = mapped_values.where(
            mapped_values.notna(),
            original,
        )

        standardized = standardized.mask(missing_mask, pd.NA)

        changed_mask = (
            original.notna()
            & (original != standardized).fillna(False)
        )

        df[column] = standardized
        stats["categorical_values_standardized"] += int(
            changed_mask.sum()
        )

    return df


def standardize_regular_date_column(df, dataset_name, column, stats):
    if column not in df.columns:
        return df

    raw_values = df[column].astype("string")
    missing_mask = get_generic_missing_mask(raw_values)

    if missing_mask.sum() > 0:
        raise ValueError(
            f"{dataset_name}: Missing values found in required "
            f"date column '{column}'."
        )

    parsed_dates = pd.to_datetime(
        raw_values,
        format=DATE_FORMAT,
        errors="coerce",
    )

    invalid_mask = parsed_dates.isna()

    if invalid_mask.sum() > 0:
        invalid_examples = raw_values[invalid_mask].head(5).tolist()

        raise ValueError(
            f"{dataset_name}: Invalid date values in '{column}' -> "
            f"{invalid_examples}"
        )

    df[column] = parsed_dates.dt.strftime("%Y-%m-%d")

    stats["date_columns_standardized"].append(column)
    stats["date_values_standardized"] += len(df)

    return df


def standardize_month_column(df, dataset_name, column, stats):
    if column not in df.columns:
        return df

    raw_values = df[column].astype("string")
    missing_mask = get_generic_missing_mask(raw_values)

    if missing_mask.sum() > 0:
        raise ValueError(
            f"{dataset_name}: Missing values found in required "
            f"month column '{column}'."
        )

    parsed_months = pd.to_datetime(
        raw_values,
        format="%Y-%m",
        errors="coerce",
    )

    invalid_mask = parsed_months.isna()

    if invalid_mask.sum() > 0:
        invalid_examples = raw_values[invalid_mask].head(5).tolist()

        raise ValueError(
            f"{dataset_name}: Invalid month values in '{column}' -> "
            f"{invalid_examples}"
        )

    df[column] = parsed_months.dt.strftime("%Y-%m")
    stats["month_columns_standardized"].append(column)

    return df


def standardize_regular_numeric_columns(
    df,
    dataset_name,
    config,
    stats,
):
    for column in config["numeric_columns"]:
        if column not in df.columns:
            continue

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
            invalid_examples = raw_values[invalid_mask].head(5).tolist()

            raise ValueError(
                f"{dataset_name}: Non-numeric values in '{column}' -> "
                f"{invalid_examples}"
            )

        if column in config["integer_columns"]:
            non_integer_mask = (
                numeric_values.notna()
                & ((numeric_values % 1) != 0)
            )

            if non_integer_mask.sum() > 0:
                invalid_examples = (
                    numeric_values[non_integer_mask]
                    .head(5)
                    .tolist()
                )

                raise ValueError(
                    f"{dataset_name}: Non-integer values in "
                    f"'{column}' -> {invalid_examples}"
                )

            df[column] = numeric_values.astype("Int64")

        else:
            df[column] = (
                numeric_values
                .astype("Float64")
                .round(2)
            )

        stats["numeric_columns_standardized"].append(column)

    return df


def validate_product_structure(products_df):
    required_columns = {
        "product_id",
        "is_perishable",
        "shelf_life_days",
    }

    missing_columns = required_columns - set(products_df.columns)

    if missing_columns:
        raise ValueError(
            "products_data.csv: Missing required columns -> "
            f"{sorted(missing_columns)}"
        )

    if products_df["product_id"].isna().sum() > 0:
        raise ValueError(
            "products_data.csv: Missing product_id values found."
        )

    duplicate_product_ids = products_df.loc[
        products_df["product_id"].duplicated(),
        "product_id",
    ].tolist()

    if duplicate_product_ids:
        raise ValueError(
            "products_data.csv: Duplicate product_id values -> "
            f"{duplicate_product_ids[:10]}"
        )

    invalid_flags = products_df.loc[
        products_df["is_perishable"].notna()
        & ~products_df["is_perishable"].isin(["Yes", "No"]),
        "is_perishable",
    ].unique()

    if len(invalid_flags) > 0:
        raise ValueError(
            "products_data.csv: is_perishable must contain only "
            f"Yes or No. Invalid values -> {list(invalid_flags)}"
        )

    if products_df["is_perishable"].isna().sum() > 0:
        raise ValueError(
            "products_data.csv: Missing is_perishable values found."
        )


def clean_shelf_life_days(products_df, stats):
    raw_values = products_df["shelf_life_days"].astype("string")

    is_perishable_yes = products_df["is_perishable"] == "Yes"
    is_perishable_no = products_df["is_perishable"] == "No"

    missing_mask = get_generic_missing_mask(raw_values)

    numeric_values = pd.to_numeric(
        raw_values.mask(missing_mask, pd.NA),
        errors="coerce",
    )

    invalid_perishable_mask = (
        is_perishable_yes
        & ~missing_mask
        & numeric_values.isna()
    )

    if invalid_perishable_mask.sum() > 0:
        invalid_examples = raw_values[
            invalid_perishable_mask
        ].head(5).tolist()

        raise ValueError(
            "products_data.csv: Invalid shelf_life_days values "
            f"for perishable products -> {invalid_examples}"
        )

    non_integer_mask = (
        is_perishable_yes
        & numeric_values.notna()
        & ((numeric_values % 1) != 0)
    )

    if non_integer_mask.sum() > 0:
        invalid_examples = numeric_values[
            non_integer_mask
        ].head(5).tolist()

        raise ValueError(
            "products_data.csv: shelf_life_days must contain "
            f"whole numbers -> {invalid_examples}"
        )

    invalid_shelf_life_mask = (
        is_perishable_yes
        & numeric_values.notna()
        & (numeric_values <= 0)
    )

    if invalid_shelf_life_mask.sum() > 0:
        invalid_examples = numeric_values[
            invalid_shelf_life_mask
        ].head(5).tolist()

        raise ValueError(
            "products_data.csv: shelf_life_days must be greater "
            f"than zero -> {invalid_examples}"
        )

    cleaned_values = pd.Series(
        pd.NA,
        index=products_df.index,
        dtype="string",
    )

    cleaned_values.loc[is_perishable_no] = "NA"

    valid_perishable_mask = (
        is_perishable_yes
        & numeric_values.notna()
    )

    formatted_values = (
        numeric_values
        .astype("Int64")
        .astype("string")
    )

    cleaned_values.loc[valid_perishable_mask] = (
        formatted_values.loc[valid_perishable_mask]
    )

    products_df["shelf_life_days"] = cleaned_values

    stats["perishable_missing_shelf_life"] = int(
        (is_perishable_yes & cleaned_values.isna()).sum()
    )

    stats["non_perishable_shelf_life_set_to_na"] = int(
        is_perishable_no.sum()
    )

    return products_df


def create_product_perishability_map(products_df):
    return products_df.set_index("product_id")[
        "is_perishable"
    ].to_dict()


def clean_expiry_date(
    inventory_df,
    product_perishability_map,
    stats,
):
    if "product_id" not in inventory_df.columns:
        raise ValueError(
            "inventory_data.csv: product_id column is required."
        )

    if "expiry_date" not in inventory_df.columns:
        raise ValueError(
            "inventory_data.csv: expiry_date column is required."
        )

    is_perishable = inventory_df["product_id"].map(
        product_perishability_map
    )

    unmapped_product_ids = inventory_df.loc[
        is_perishable.isna(),
        "product_id",
    ].dropna().unique()

    if len(unmapped_product_ids) > 0:
        raise ValueError(
            "inventory_data.csv: Product IDs missing from "
            "products_data.csv -> "
            f"{list(unmapped_product_ids[:10])}"
        )

    raw_values = inventory_df["expiry_date"].astype("string")

    is_perishable_yes = is_perishable == "Yes"
    is_perishable_no = is_perishable == "No"

    missing_mask = get_generic_missing_mask(raw_values)

    candidate_dates = raw_values.mask(
        missing_mask,
        pd.NA,
    )

    parsed_dates = pd.to_datetime(
        candidate_dates,
        format=DATE_FORMAT,
        errors="coerce",
    )

    invalid_perishable_mask = (
        is_perishable_yes
        & ~missing_mask
        & parsed_dates.isna()
    )

    if invalid_perishable_mask.sum() > 0:
        invalid_examples = raw_values[
            invalid_perishable_mask
        ].head(5).tolist()

        raise ValueError(
            "inventory_data.csv: Invalid expiry_date values "
            f"for perishable products -> {invalid_examples}"
        )

    cleaned_values = pd.Series(
        pd.NA,
        index=inventory_df.index,
        dtype="string",
    )

    cleaned_values.loc[is_perishable_no] = "NA"

    valid_perishable_mask = (
        is_perishable_yes
        & parsed_dates.notna()
    )

    cleaned_values.loc[valid_perishable_mask] = (
        parsed_dates.loc[valid_perishable_mask]
        .dt.strftime("%Y-%m-%d")
    )

    inventory_df["expiry_date"] = cleaned_values

    stats["perishable_missing_expiry"] = int(
        (is_perishable_yes & cleaned_values.isna()).sum()
    )

    stats["non_perishable_expiry_set_to_na"] = int(
        is_perishable_no.sum()
    )

    return inventory_df


def remove_unneeded_columns(df, config, stats):
    columns_to_remove = config.get("drop_columns", [])

    existing_columns = [
        column
        for column in columns_to_remove
        if column in df.columns
    ]

    if existing_columns:
        df = df.drop(columns=existing_columns)

    stats["columns_removed"] = existing_columns

    return df


def normalize_remaining_missing_values(
    df,
    protected_columns,
    stats,
):
    for column in df.columns:
        if column in protected_columns:
            continue

        if not (
            pd.api.types.is_object_dtype(df[column])
            or pd.api.types.is_string_dtype(df[column])
        ):
            continue

        original = df[column].astype("string")
        missing_mask = get_generic_missing_mask(original)

        df[column] = original.mask(missing_mask, pd.NA)

        stats["generic_missing_values_standardized"] += int(
            missing_mask.sum()
        )

    return df


def create_initial_stats(filename, config, df):
    return {
        "input_file": filename,
        "output_file": config["output"],
        "original_rows": len(df),
        "original_columns": len(df.columns),
        "final_rows": 0,
        "duplicates_removed": 0,
        "columns_removed": [],
        "text_values_normalized": 0,
        "id_values_standardized": 0,
        "categorical_values_standardized": 0,
        "generic_missing_values_standardized": 0,
        "date_values_standardized": 0,
        "date_columns_standardized": [],
        "month_columns_standardized": [],
        "numeric_columns_standardized": [],
        "perishable_missing_shelf_life": 0,
        "non_perishable_shelf_life_set_to_na": 0,
        "perishable_missing_expiry": 0,
        "non_perishable_expiry_set_to_na": 0,
    }


def clean_dataset(
    filename,
    config,
    product_perishability_map=None,
):
    input_path = RAW_DATA_DIR / filename

    if not input_path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: {input_path}"
        )

    df = pd.read_csv(
        input_path,
        dtype="string",
        keep_default_na=False,
    )

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    stats = create_initial_stats(filename, config, df)

    df = normalize_text_columns(df, stats)
    df = standardize_id_columns(df, stats)
    df = standardize_categorical_columns(df, config, stats)

    for column in config["date_columns"]:
        df = standardize_regular_date_column(
            df,
            filename,
            column,
            stats,
        )

    for column in config["month_columns"]:
        df = standardize_month_column(
            df,
            filename,
            column,
            stats,
        )

    df = standardize_regular_numeric_columns(
        df,
        filename,
        config,
        stats,
    )

    protected_columns = set()

    if filename == "products_data.csv":
        validate_product_structure(df)

        df = clean_shelf_life_days(df, stats)

        product_perishability_map = create_product_perishability_map(df)

        protected_columns.add("shelf_life_days")

    if filename == "inventory_data.csv":
        if product_perishability_map is None:
            raise ValueError(
                "Inventory cleaning requires cleaned product "
                "perishability information."
            )

        df = clean_expiry_date(
            df,
            product_perishability_map,
            stats,
        )

        protected_columns.add("expiry_date")

    df = remove_unneeded_columns(
        df,
        config,
        stats,
    )

    df = normalize_remaining_missing_values(
        df,
        protected_columns,
        stats,
    )

    stats["duplicates_removed"] = int(df.duplicated().sum())

    df = df.drop_duplicates()

    stats["final_rows"] = len(df)

    return df, stats, product_perishability_map


def save_cleaned_dataset(df, stats):
    output_path = PROCESSED_DATA_DIR / stats["output_file"]

    df.to_csv(
        output_path,
        index=False,
        na_rep="",
    )

    print(f"Cleaned: {stats['input_file']}")
    print(f"Saved:   {output_path}")
    print(f"Rows:    {stats['original_rows']} -> {stats['final_rows']}")
    print(f"Duplicates removed: {stats['duplicates_removed']}")

    if stats["columns_removed"]:
        print(
            "Columns removed: "
            f"{', '.join(stats['columns_removed'])}"
        )

    print("-" * 60)


def create_cleaning_report():
    report_path = REPORT_DIR / "data_cleaning_report.txt"

    report_lines = [
        "DATA CLEANING REPORT",
        "=" * 60,
        "",
        "Special handling:",
        "- products_data.csv -> is_perishable and shelf_life_days",
        "- inventory_data.csv -> expiry_date",
        "- Inventory expiry checks use the product_id relationship.",
        "- is_perishable is not added to inventory_cleaned.csv.",
        "",
        "Rules:",
        "- Non-perishable products have shelf_life_days as literal NA.",
        "- Non-perishable inventory has expiry_date as literal NA.",
        "- Perishable products require valid shelf_life_days.",
        "- Perishable inventory requires valid expiry_date.",
        "",
        "All other columns:",
        "- NA, N/A, None, Null, Nan, and blank values are treated",
        "  as missing values and are saved as blanks.",
        "",
        "All other date columns:",
        "- Are mandatory.",
        "- NA or blank values stop the cleaning process with an error.",
        "",
        "Removed from processed output:",
        "- reorder_trigger_level is removed from inventory_cleaned.csv.",
        "",
        "DATASET DETAILS",
        "=" * 60,
    ]

    for log in cleaning_logs:
        report_lines.extend([
            "",
            f"Dataset: {log['input_file']}",
            f"Processed file: {log['output_file']}",
            f"Rows: {log['original_rows']} -> {log['final_rows']}",
            f"Columns before cleaning: {log['original_columns']}",
            f"Duplicates removed: {log['duplicates_removed']}",
            (
                "Columns removed: "
                f"{', '.join(log['columns_removed']) or 'None'}"
            ),
            f"Text values normalized: {log['text_values_normalized']}",
            f"ID values standardized: {log['id_values_standardized']}",
            (
                "Categorical labels standardized: "
                f"{log['categorical_values_standardized']}"
            ),
            (
                "Generic missing values standardized: "
                f"{log['generic_missing_values_standardized']}"
            ),
            (
                "Date columns standardized: "
                f"{', '.join(log['date_columns_standardized']) or 'None'}"
            ),
            (
                "Month columns standardized: "
                f"{', '.join(log['month_columns_standardized']) or 'None'}"
            ),
            (
                "Numeric columns standardized: "
                f"{', '.join(log['numeric_columns_standardized']) or 'None'}"
            ),
            (
                "Perishable products with missing shelf life: "
                f"{log['perishable_missing_shelf_life']}"
            ),
            (
                "Non-perishable shelf life values set to NA: "
                f"{log['non_perishable_shelf_life_set_to_na']}"
            ),
            (
                "Perishable inventory rows with missing expiry date: "
                f"{log['perishable_missing_expiry']}"
            ),
            (
                "Non-perishable expiry values set to NA: "
                f"{log['non_perishable_expiry_set_to_na']}"
            ),
        ])

    report_path.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("Data cleaning completed successfully.")
    print(f"Cleaning report saved at: {report_path}")


def main():
    product_perishability_map = None

    try:
        for filename in PROCESSING_ORDER:
            config = DATASETS[filename]

            cleaned_df, stats, product_perishability_map = clean_dataset(
                filename,
                config,
                product_perishability_map,
            )

            save_cleaned_dataset(cleaned_df, stats)

            cleaning_logs.append(stats)

    except Exception as error:
        print("\nData cleaning stopped.")
        print(f"Reason: {error}")
        raise

    create_cleaning_report()


if __name__ == "__main__":
    main()