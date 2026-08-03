from app.database import connection


def check_database_ready() -> None:
    with connection() as db:
        db.execute("SELECT 1").fetchone()
