from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.database import get_database_engine


engine: Engine = get_database_engine()


def check_database_connection() -> dict[str, str]:
    """Test the PostgreSQL connection and return database information."""

    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT
                    current_database() AS database_name;
                """
            )
        ).mappings().one()

    return {
        "database_name": str(result["database_name"]),
    }