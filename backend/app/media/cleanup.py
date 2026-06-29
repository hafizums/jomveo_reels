import shutil
from collections.abc import Iterable
from pathlib import Path

from backend.app.core.errors import StorageError


def cleanup_paths(paths: Iterable[Path], root: Path) -> None:
    resolved_root = root.expanduser().resolve()
    for path in paths:
        resolved_path = path.expanduser().resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError as exc:
            raise StorageError("Refusing to clean a path outside the storage root.") from exc
        if resolved_path.is_dir():
            shutil.rmtree(resolved_path, ignore_errors=True)
        else:
            resolved_path.unlink(missing_ok=True)
