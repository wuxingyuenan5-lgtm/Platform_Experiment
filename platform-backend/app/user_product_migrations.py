from __future__ import annotations

from app.database import connection
from app.schema_migrations import Migration, apply_migrations


USER_PRODUCT_MIGRATIONS: tuple[Migration, ...] = (
    Migration(
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
        apply_migrations(db, USER_PRODUCT_MIGRATIONS)
