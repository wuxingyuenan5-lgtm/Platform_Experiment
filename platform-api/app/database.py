from __future__ import annotations

from app.database_bootstrap import SCHEMA_SQL as SCHEMA_SQL
from app.database_bootstrap import bootstrap_database
from app.database_bootstrap import ensure_column as ensure_column
from app.database_bootstrap import migrate_schema as migrate_schema
from app.database_connection import connection as connection
from app.database_connection import database_path as database_path
from app.database_seeds import seed_reference_data as seed_reference_data


def initialize_database() -> None:
    with connection() as db:
        bootstrap_database(db)
        seed_reference_data(db)
