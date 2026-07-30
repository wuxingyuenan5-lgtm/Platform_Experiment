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
        name="user-research-watchlists",
        statements=(
            """
            CREATE TABLE user_research_watchlists (
                user_id TEXT NOT NULL,
                market TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(user_id, market),
                CHECK (market IN ('a_share')),
                CHECK (version >= 0),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE user_research_watchlist_items (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                market TEXT NOT NULL,
                security_code TEXT NOT NULL,
                security_name TEXT NOT NULL,
                group_name TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, market, security_code),
                CHECK (length(security_code) = 6),
                CHECK (sort_order >= 0),
                FOREIGN KEY(user_id, market)
                    REFERENCES user_research_watchlists(user_id, market)
                    ON DELETE CASCADE
            )
            """,
            """
            CREATE INDEX idx_user_research_watchlist_items_order
            ON user_research_watchlist_items(user_id, market, sort_order)
            """,
        ),
    ),
)


def apply_user_product_migrations() -> None:
    with connection() as db:
        schema_migrations.apply_migrations(db, USER_PRODUCT_MIGRATIONS)
