from __future__ import annotations

import hashlib
import re
import shutil
import zipfile
from pathlib import Path

from app.config import get_settings

USER_PLATFORM_TABLES = (
    "users",
    "user_sessions",
    "password_reset_tickets",
    "funds",
    "member_fund_holdings",
    "fund_nav_snapshots",
)
SAFE_AVATAR_FILE = re.compile(r"[0-9a-f-]+\.webp")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def avatar_archive_manifest(source_root: str, destination: Path) -> dict[str, object]:
    root = Path(source_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    avatar_files: list[Path] = []
    total_bytes = 0
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if (
            entry.is_symlink()
            or not entry.is_file()
            or SAFE_AVATAR_FILE.fullmatch(entry.name) is None
        ):
            raise RuntimeError("Avatar directory contains an unsupported entry")
        avatar_files.append(entry)
        total_bytes += entry.stat().st_size

    with zipfile.ZipFile(
        destination,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for entry in avatar_files:
            archive.write(entry, arcname=entry.name)

    return {
        "logicalName": "avatar_archive",
        "fileName": destination.name,
        "sourceFileName": root.name,
        "sha256": _sha256_file(destination),
        "sizeBytes": destination.stat().st_size,
        "tableCounts": {},
        "integrity": "ok",
        "fileCount": len(avatar_files),
        "totalBytes": total_bytes,
    }


def restore_avatar_archive(
    source: Path,
    destination: Path,
    *,
    expected_file_count: int,
    expected_total_bytes: int,
) -> dict[str, object]:
    destination.mkdir(parents=False, exist_ok=False)
    destination_root = destination.resolve()
    restored_count = 0
    restored_bytes = 0
    seen: set[str] = set()
    settings = get_settings()

    with zipfile.ZipFile(source, mode="r") as archive:
        entries = archive.infolist()
        if len(entries) != expected_file_count:
            raise RuntimeError("Avatar archive file count differs from the backup manifest")
        for entry in entries:
            file_name = entry.filename
            unix_mode = entry.external_attr >> 16
            is_symlink = (unix_mode & 0o170000) == 0o120000
            if (
                entry.is_dir()
                or is_symlink
                or file_name in seen
                or Path(file_name).name != file_name
                or SAFE_AVATAR_FILE.fullmatch(file_name) is None
                or entry.file_size > settings.avatar_max_bytes
            ):
                raise RuntimeError("Avatar archive contains an unsafe entry")
            seen.add(file_name)
            target = (destination_root / file_name).resolve()
            if target.parent != destination_root:
                raise RuntimeError("Avatar archive entry escapes the restore directory")
            with archive.open(entry, mode="r") as source_handle, target.open("xb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle)
            restored_count += 1
            restored_bytes += target.stat().st_size

    if restored_bytes != expected_total_bytes:
        raise RuntimeError("Avatar archive byte count differs from the backup manifest")
    return {
        "status": "ok",
        "fileCount": restored_count,
        "totalBytes": restored_bytes,
    }
