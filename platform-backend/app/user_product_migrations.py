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
    schema_migrations.Migration(
        version=8,
        name="user-research-watchlist",
        statements=(
            """
            CREATE TABLE user_research_watchlists (
                user_id TEXT PRIMARY KEY,
                items_json TEXT NOT NULL,
                row_version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK (row_version >= 1),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE INDEX idx_user_research_watchlists_updated
            ON user_research_watchlists(updated_at DESC)
            """,
        ),
    ),
)


def apply_user_product_migrations() -> None:
    with connection() as db:
        schema_migrations.apply_migrations(db, USER_PRODUCT_MIGRATIONS)
