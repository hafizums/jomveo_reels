import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from backend.app.core.errors import UnsafePathError

SAFE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
UNSAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_object_key(key: str) -> str:
    normalized = key.strip().replace("\\", "/")
    if not normalized or normalized.startswith("/") or PureWindowsPath(normalized).drive:
        raise UnsafePathError("Storage key must be a relative path.")
    parts = PurePosixPath(normalized).parts
    if any(part in {"", ".", ".."} or not SAFE_SEGMENT_PATTERN.fullmatch(part) for part in parts):
        raise UnsafePathError("Storage key contains an unsafe path segment.")
    return "/".join(parts)


def safe_join(root: Path, key: str) -> Path:
    normalized = normalize_object_key(key)
    resolved_root = root.expanduser().resolve()
    destination = (resolved_root / Path(*normalized.split("/"))).resolve()
    try:
        destination.relative_to(resolved_root)
    except ValueError as exc:
        raise UnsafePathError("Storage key resolves outside the storage root.") from exc
    return destination


def sanitize_filename(name: str, fallback: str = "file") -> str:
    basename = PurePosixPath(name.replace("\\", "/")).name.strip()
    sanitized = UNSAFE_FILENAME_PATTERN.sub("-", basename).strip(" .-_")
    if sanitized in {"", ".", ".."}:
        sanitized = fallback
    stem = Path(sanitized).stem[:120].strip(" .-_") or fallback
    suffix = Path(sanitized).suffix.lower()[:16]
    return f"{stem}{suffix}"


def make_object_key(category: str, filename: str) -> str:
    normalized_category = normalize_object_key(category).rstrip("/")
    return normalize_object_key(f"{normalized_category}/{sanitize_filename(filename)}")
