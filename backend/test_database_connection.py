import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

required_variables = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
]

missing_variables = [
    variable for variable in required_variables
    if not os.getenv(variable)
]

if missing_variables:
    print("Database connection failed.")
    print(f"Missing values in .env: {', '.join(missing_variables)}")
    sys.exit(1)

database_url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=int(os.getenv("POSTGRES_PORT")),
    database=os.getenv("POSTGRES_DB"),
)

try:
    engine = create_engine(database_url)

    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    current_database() AS database_name,
                    current_user AS connected_user,
                    version() AS postgresql_version;
            """)
        ).mappings().one()

    print("PostgreSQL connection successful.")
    print(f"Database: {result['database_name']}")
    print(f"User: {result['connected_user']}")
    print(f"Version: {result['postgresql_version']}")

except Exception as error:
    print("Database connection failed.")
    print(f"Error: {error}")
    sys.exit(1)