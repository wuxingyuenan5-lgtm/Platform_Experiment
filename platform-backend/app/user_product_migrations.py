from __future__ import annotations

import app.schema_migrations as schema_migrations
from app.database import connection


USER_PRODUCT_MIGRATIONS: tuple[schema_migrations.Migration, ...] = (
    schema_migrations.Migration(
        version=7,
        name="user-admin-operational-note",
        statements=(
            """
            ALTER TABLE users ADD COLUMN admin_note TEXT
            """,
        ),
    ),
)


def apply_user_product_migrations() -> None:
    with connection() as db:
        schema_migrations.apply_migrations(db, USER_PRODUCT_MIGRATIONS)
