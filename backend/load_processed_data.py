import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

load_dotenv(BASE_DIR / ".env")

MISSING_TEXT_VALUES = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "nan",
}

DATASETS = [
    {
        "file_name": "vendors_cleaned.csv",
        "table_name": "vendors",
        "expected_columns": [
            "vendor_id",
            "vendor_name",
            "vendor_category",
            "contact_person",
            "city",
            "state",
            "region",
            "average_delivery_days",
            "rating",
            "payment_terms",
            "supply_status",
        ],
        "date_columns": [],
        "integer_columns": [
            "average_delivery_days",
        ],
        "decimal_columns": [
            "rating",
        ],
    },
    {
        "file_name": "employees_cleaned.csv",
        "table_name": "employees",
        "expected_columns": [
            "employee_id",
            "employee_name",
            "role",
            "department",
            "store_id",
            "region",
            "email",
            "monthly_target",
            "performance_status",
            "employment_status",
        ],
        "date_columns": [],
        "integer_columns": [],
        "decimal_columns": [
            "monthly_target",
        ],
    },
    {
        "file_name": "stores_cleaned.csv",
        "table_name": "stores",
        "expected_columns": [
            "store_id",
            "store_name",
            "city",
            "state",
            "region",
            "store_type",
            "manager_id",
            "opening_date",
            "monthly_sales_target",
            "operational_status",
        ],
        "date_columns": [
            "opening_date",
        ],
        "integer_columns": [],
        "decimal_columns": [
            "monthly_sales_target",
        ],
    },
    {
        "file_name": "products_cleaned.csv",
        "table_name": "products",
        "expected_columns": [
            "product_id",
            "product_name",
            "category",
            "sub_category",
            "brand",
            "unit_price",
            "cost_price",
            "margin_percent",
            "reorder_level",
            "shelf_life_days",
            "is_perishable",
            "vendor_id",
        ],
        "date_columns": [],
        "integer_columns": [
            "reorder_level",
            "shelf_life_days",
        ],
        "decimal_columns": [
            "unit_price",
            "cost_price",
            "margin_percent",
        ],
    },
    {
        "file_name": "sales_cleaned.csv",
        "table_name": "sales",
        "expected_columns": [
            "sale_id",
            "date",
            "store_id",
            "store_name",
            "region",
            "product_id",
            "product_name",
            "category",
            "employee_id",
            "quantity_sold",
            "unit_price",
            "discount_percent",
            "total_sales",
            "total_cost",
            "profit",
            "payment_status",
        ],
        "date_columns": [
            "date",
        ],
        "integer_columns": [
            "quantity_sold",
        ],
        "decimal_columns": [
            "unit_price",
            "discount_percent",
            "total_sales",
            "total_cost",
            "profit",
        ],
    },
    {
        "file_name": "inventory_cleaned.csv",
        "table_name": "inventory",
        "expected_columns": [
            "inventory_id",
            "date",
            "store_id",
            "store_name",
            "product_id",
            "product_name",
            "category",
            "vendor_id",
            "current_stock",
            "reorder_level",
            "stock_status",
            "reorder_required",
            "expiry_date",
        ],
        "date_columns": [
            "date",
            "expiry_date",
        ],
        "integer_columns": [
            "current_stock",
            "reorder_level",
        ],
        "decimal_columns": [],
    },
    {
        "file_name": "complaints_cleaned.csv",
        "table_name": "complaints",
        "expected_columns": [
            "complaint_id",
            "date",
            "customer_id",
            "store_id",
            "store_name",
            "region",
            "product_id",
            "product_name",
            "category",
            "complaint_type",
            "complaint_description",
            "severity",
            "status",
            "assigned_employee_id",
            "resolution_time_days",
        ],
        "date_columns": [
            "date",
        ],
        "integer_columns": [
            "resolution_time_days",
        ],
        "decimal_columns": [],
    },
    {
        "file_name": "finance_cleaned.csv",
        "table_name": "finance",
        "expected_columns": [
            "finance_id",
            "month",
            "store_id",
            "store_name",
            "region",
            "monthly_sales_target",
            "total_revenue",
            "total_cost",
            "gross_profit",
            "operating_expense",
            "operating_profit",
            "target_achievement_percent",
            "risk_status",
        ],
        "date_columns": [],
        "integer_columns": [],
        "decimal_columns": [
            "monthly_sales_target",
            "total_revenue",
            "total_cost",
            "gross_profit",
            "operating_expense",
            "operating_profit",
            "target_achievement_percent",
        ],
    },
    {
        "file_name": "vendor_deliveries_cleaned.csv",
        "table_name": "vendor_deliveries",
        "expected_columns": [
            "purchase_order_id",
            "order_date",
            "expected_delivery_date",
            "actual_delivery_date",
            "store_id",
            "store_name",
            "vendor_id",
            "vendor_name",
            "product_id",
            "product_name",
            "ordered_quantity",
            "received_quantity",
            "unit_cost",
            "purchase_value",
            "delay_days",
            "delivery_status",
            "quality_rating",
            "assigned_employee_id",
        ],
        "date_columns": [
            "order_date",
            "expected_delivery_date",
            "actual_delivery_date",
        ],
        "integer_columns": [
            "ordered_quantity",
            "received_quantity",
            "delay_days",
        ],
        "decimal_columns": [
            "unit_cost",
            "purchase_value",
            "quality_rating",
        ],
    },
]


def get_database_url():
    required_variables = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise ValueError(
            "Missing database environment variables: "
            f"{', '.join(missing_variables)}"
        )

    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=os.getenv("POSTGRES_DB"),
    )


def standardize_missing_values(dataframe):
    for column in dataframe.columns:
        values = dataframe[column].astype("string").str.strip()

        missing_mask = (
            values.isna()
            | values.str.lower()
            .isin(MISSING_TEXT_VALUES)
            .fillna(False)
        )

        dataframe[column] = values.mask(missing_mask, pd.NA)

    return dataframe


def validate_columns(dataframe, config):
    expected_columns = config["expected_columns"]
    actual_columns = dataframe.columns.tolist()

    missing_columns = [
        column
        for column in expected_columns
        if column not in actual_columns
    ]

    extra_columns = [
        column
        for column in actual_columns
        if column not in expected_columns
    ]

    if missing_columns or extra_columns:
        raise ValueError(
            f"{config['file_name']}: Column mismatch.\n"
            f"Missing columns: {missing_columns or 'None'}\n"
            f"Unexpected columns: {extra_columns or 'None'}"
        )

    dataframe = dataframe[expected_columns]

    return dataframe


def convert_date_columns(dataframe, config):
    for column in config["date_columns"]:
        parsed_dates = pd.to_datetime(
            dataframe[column],
            format="%Y-%m-%d",
            errors="coerce",
        )

        invalid_mask = (
            dataframe[column].notna()
            & parsed_dates.isna()
        )

        if invalid_mask.sum() > 0:
            invalid_values = dataframe.loc[
                invalid_mask,
                column,
            ].head(5).tolist()

            raise ValueError(
                f"{config['file_name']}: Invalid dates in "
                f"{column} -> {invalid_values}"
            )

        dataframe[column] = parsed_dates.dt.date

    return dataframe


def convert_numeric_columns(dataframe, config):
    numeric_columns = (
        config["integer_columns"]
        + config["decimal_columns"]
    )

    for column in numeric_columns:
        numeric_values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        invalid_mask = (
            dataframe[column].notna()
            & numeric_values.isna()
        )

        if invalid_mask.sum() > 0:
            invalid_values = dataframe.loc[
                invalid_mask,
                column,
            ].head(5).tolist()

            raise ValueError(
                f"{config['file_name']}: Non-numeric values in "
                f"{column} -> {invalid_values}"
            )

        if column in config["integer_columns"]:
            non_integer_mask = (
                numeric_values.notna()
                & ((numeric_values % 1) != 0)
            )

            if non_integer_mask.sum() > 0:
                invalid_values = numeric_values[
                    non_integer_mask
                ].head(5).tolist()

                raise ValueError(
                    f"{config['file_name']}: Non-integer values in "
                    f"{column} -> {invalid_values}"
                )

            dataframe[column] = numeric_values.astype("Int64")

        else:
            dataframe[column] = numeric_values.astype(
                "Float64"
            ).round(2)

    return dataframe


def prepare_dataset(config):
    file_path = PROCESSED_DATA_DIR / config["file_name"]

    if not file_path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found: {file_path}"
        )

    dataframe = pd.read_csv(
        file_path,
        dtype="string",
        keep_default_na=False,
    )

    dataframe = standardize_missing_values(dataframe)
    dataframe = validate_columns(dataframe, config)
    dataframe = convert_date_columns(dataframe, config)
    dataframe = convert_numeric_columns(dataframe, config)

    return dataframe


def clear_existing_business_data(connection):
    connection.execute(
        text(
            """
            TRUNCATE TABLE
                vendor_deliveries,
                complaints,
                inventory,
                sales,
                finance,
                products,
                stores,
                employees,
                vendors
            RESTART IDENTITY;
            """
        )
    )


def insert_import_log(
    connection,
    dataset_name,
    source_file_name,
    total_rows,
    successful_rows,
    failed_rows,
    import_status,
    error_message=None,
):
    connection.execute(
        text(
            """
            INSERT INTO data_import_logs (
                dataset_name,
                source_file_name,
                total_rows,
                successful_rows,
                failed_rows,
                import_status,
                error_message
            )
            VALUES (
                :dataset_name,
                :source_file_name,
                :total_rows,
                :successful_rows,
                :failed_rows,
                :import_status,
                :error_message
            );
            """
        ),
        {
            "dataset_name": dataset_name,
            "source_file_name": source_file_name,
            "total_rows": total_rows,
            "successful_rows": successful_rows,
            "failed_rows": failed_rows,
            "import_status": import_status,
            "error_message": error_message,
        },
    )


def verify_row_counts(connection):
    print("\nPOST-IMPORT ROW COUNTS")
    print("-" * 60)

    for config in DATASETS:
        table_name = config["table_name"]

        row_count = connection.execute(
            text(f"SELECT COUNT(*) FROM {table_name};")
        ).scalar_one()

        print(f"{table_name}: {row_count} rows")


def main():
    database_url = get_database_url()
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    prepared_datasets = []
    current_config = None
    current_row_count = 0

    try:
        print("Preparing cleaned datasets...")

        for config in DATASETS:
            dataframe = prepare_dataset(config)

            prepared_datasets.append(
                {
                    "config": config,
                    "dataframe": dataframe,
                }
            )

            print(
                f"Prepared: {config['file_name']} "
                f"({len(dataframe)} rows)"
            )

        print("\nConnecting to PostgreSQL...")

        with engine.begin() as connection:
            database_name = connection.execute(
                text("SELECT current_database();")
            ).scalar_one()

            print(f"Connected to database: {database_name}")

            clear_existing_business_data(connection)

            print("Existing business data cleared.")
            print("\nLoading processed datasets...")
            print("-" * 60)

            for item in prepared_datasets:
                current_config = item["config"]
                dataframe = item["dataframe"]
                current_row_count = len(dataframe)

                dataframe.to_sql(
                    name=current_config["table_name"],
                    con=connection,
                    if_exists="append",
                    index=False,
                    method="multi",
                    chunksize=1000,
                )

                insert_import_log(
                    connection=connection,
                    dataset_name=current_config["table_name"],
                    source_file_name=current_config["file_name"],
                    total_rows=current_row_count,
                    successful_rows=current_row_count,
                    failed_rows=0,
                    import_status="Success",
                )

                print(
                    f"Loaded: {current_config['table_name']} "
                    f"({current_row_count} rows)"
                )

            verify_row_counts(connection)

        print("\nProcessed CSV data loaded successfully.")

    except Exception as error:
        print("\nData loading failed.")
        print(f"Reason: {error}")

        if current_config is not None:
            try:
                with engine.begin() as connection:
                    insert_import_log(
                        connection=connection,
                        dataset_name=current_config["table_name"],
                        source_file_name=current_config["file_name"],
                        total_rows=current_row_count,
                        successful_rows=0,
                        failed_rows=current_row_count,
                        import_status="Failed",
                        error_message=str(error)[:1000],
                    )
            except Exception:
                pass

        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()