from __future__ import annotations

import io
import os
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.database import connection
from app.user_avatar_repository import update_user_avatar
from app.user_repository import (
    ConcurrentUserUpdateError,
    UserNotFoundError,
    get_user_profile,
    insert_audit_event,
)

ALLOWED_INPUT_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


class AvatarServiceError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class AvatarMutationResult:
    avatar_key: str | None
    row_version: int


def _avatar_root() -> Path:
    root = Path(get_settings().avatar_data_directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path_for_key(key: str) -> Path:
    if not key or any(character not in "0123456789abcdef-" for character in key):
        raise AvatarServiceError(404, "avatar_not_found", "Avatar does not exist")
    root = _avatar_root()
    path = (root / f"{key}.webp").resolve()
    if path.parent != root:
        raise AvatarServiceError(404, "avatar_not_found", "Avatar does not exist")
    return path


def _unlink_best_effort(key: str | None) -> None:
    if not key:
        return
    try:
        _path_for_key(key).unlink(missing_ok=True)
    except OSError:
        return


def _encode_avatar(raw_bytes: bytes) -> bytes:
    settings = get_settings()
    if not raw_bytes:
        raise AvatarServiceError(422, "avatar_empty", "Avatar file is empty")
    if len(raw_bytes) > settings.avatar_max_bytes:
        raise AvatarServiceError(413, "avatar_too_large", "Avatar file exceeds 2 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw_bytes)) as source:
                if source.format not in ALLOWED_INPUT_FORMATS:
                    raise AvatarServiceError(
                        415,
                        "avatar_type_unsupported",
                        "Avatar must be JPEG, PNG or WebP",
                    )
                width, height = source.size
                if width < 1 or height < 1 or width * height > settings.avatar_max_pixels:
                    raise AvatarServiceError(
                        422,
                        "avatar_dimensions_invalid",
                        "Avatar dimensions are invalid or too large",
                    )
                source.load()
                normalized = ImageOps.exif_transpose(source)
                if normalized.mode not in {"RGB", "RGBA"}:
                    normalized = normalized.convert("RGBA")
                output = ImageOps.fit(
                    normalized,
                    (settings.avatar_output_size, settings.avatar_output_size),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                buffer = io.BytesIO()
                output.save(buffer, format="WEBP", quality=90, method=6)
                return buffer.getvalue()
    except AvatarServiceError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise AvatarServiceError(
            422,
            "avatar_dimensions_invalid",
            "Avatar dimensions are too large",
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise AvatarServiceError(
            422,
            "avatar_decode_failed",
            "Avatar file cannot be decoded",
        ) from exc


def replace_avatar(
    *,
    user_id: str,
    raw_bytes: bytes,
    expected_version: int,
    request_id: str,
    ip_address: str | None,
) -> AvatarMutationResult:
    encoded = _encode_avatar(raw_bytes)
    key = str(uuid4())
    root = _avatar_root()
    final_path = _path_for_key(key)
    temporary_path = root / f".{key}.tmp"
    try:
        with temporary_path.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, final_path)
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise AvatarServiceError(503, "avatar_storage_failed", "Avatar could not be stored") from exc

    timestamp = datetime.now(UTC).isoformat()
    previous_key: str | None = None
    try:
        with connection() as db:
            result = update_user_avatar(
                db,
                user_id=user_id,
                avatar_key=key,
                expected_version=expected_version,
                now=timestamp,
            )
            previous_key = result.previous_avatar_key
            insert_audit_event(
                db,
                event_type="user.avatar_changed",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=user_id,
                auth_method="session",
                result="succeeded",
                details={"action": "replace"},
                request_id=request_id,
                ip_address=ip_address,
                now=timestamp,
            )
    except ConcurrentUserUpdateError as exc:
        final_path.unlink(missing_ok=True)
        raise AvatarServiceError(409, "row_version_conflict", str(exc)) from exc
    except UserNotFoundError as exc:
        final_path.unlink(missing_ok=True)
        raise AvatarServiceError(404, "user_not_found", "User does not exist") from exc
    except Exception:
        final_path.unlink(missing_ok=True)
        raise
    _unlink_best_effort(previous_key)
    return AvatarMutationResult(avatar_key=key, row_version=expected_version + 1)


def delete_avatar(
    *,
    user_id: str,
    expected_version: int,
    request_id: str,
    ip_address: str | None,
) -> AvatarMutationResult:
    timestamp = datetime.now(UTC).isoformat()
    try:
        with connection() as db:
            result = update_user_avatar(
                db,
                user_id=user_id,
                avatar_key=None,
                expected_version=expected_version,
                now=timestamp,
            )
            insert_audit_event(
                db,
                event_type="user.avatar_changed",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=user_id,
                auth_method="session",
                result="succeeded",
                details={"action": "delete"},
                request_id=request_id,
                ip_address=ip_address,
                now=timestamp,
            )
    except ConcurrentUserUpdateError as exc:
        raise AvatarServiceError(409, "row_version_conflict", str(exc)) from exc
    except UserNotFoundError as exc:
        raise AvatarServiceError(404, "user_not_found", "User does not exist") from exc
    _unlink_best_effort(result.previous_avatar_key)
    return AvatarMutationResult(avatar_key=None, row_version=result.row_version)


def current_avatar_path(user_id: str) -> Path:
    with connection() as db:
        profile = get_user_profile(db, user_id)
    if profile is None or profile.avatar_key is None:
        raise AvatarServiceError(404, "avatar_not_found", "Avatar does not exist")
    path = _path_for_key(profile.avatar_key)
    if not path.is_file():
        raise AvatarServiceError(404, "avatar_not_found", "Avatar does not exist")
    return path
