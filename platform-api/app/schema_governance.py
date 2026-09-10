from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.schema_migrations import (
    PLATFORM_MIGRATIONS,
    list_applied_migrations,
)
from app.user_product_migrations import (
    USER_PRODUCT_MIGRATIONS,
)

ALL_PLATFORM_MIGRATIONS = tuple(
    sorted(
        (*PLATFORM_MIGRATIONS, *USER_PRODUCT_MIGRATIONS),
        key=lambda item: item.version,
    )
)


class SchemaMigrationStatus(BaseModel):
    version: int
    name: str
    checksum: str
    applied_at: datetime | None = Field(default=None, alias="appliedAt")
    status: str


class SchemaMigrationStatusResponse(BaseModel):
    status: str
    migrations: list[SchemaMigrationStatus]


settings = get_settings()
router = APIRouter(
    prefix=f"{settings.api_prefix}/ops/schema-migrations",
)


@router.get("", response_model=SchemaMigrationStatusResponse, tags=["ops"])
def schema_migration_status() -> SchemaMigrationStatusResponse:
    applied_by_version = {item["version"]: item for item in list_applied_migrations()}
    statuses: list[SchemaMigrationStatus] = []
    for migration in ALL_PLATFORM_MIGRATIONS:
        applied = applied_by_version.get(migration.version)
        applied_at = datetime.fromisoformat(applied["appliedAt"]) if applied is not None else None
        statuses.append(
            SchemaMigrationStatus(
                version=migration.version,
                name=migration.name,
                checksum=migration.checksum,
                appliedAt=applied_at,
                status="applied" if applied is not None else "pending",
            )
        )
    overall = "current" if all(item.status == "applied" for item in statuses) else "pending"
    return SchemaMigrationStatusResponse(status=overall, migrations=statuses)
