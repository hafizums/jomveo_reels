import os
import shutil
import uuid
from pathlib import Path

from backend.app.core.errors import StorageError
from backend.app.storage.base import StoredObject
from backend.app.storage.paths import normalize_object_key, safe_join


class LocalStorageBackend:
    def __init__(self, root: Path, public_url_prefix: str = "/generated") -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_url_prefix = "/" + public_url_prefix.strip("/")

    def save_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        destination = self.open_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.part")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, destination)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise StorageError("Could not save the stored object.") from exc
        return self._stored_object(key, destination, content_type)

    def save_file(
        self,
        key: str,
        source_path: Path,
        content_type: str | None = None,
    ) -> StoredObject:
        if not source_path.is_file():
            raise StorageError("Storage source file does not exist.")
        destination = self.open_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.part")
        try:
            shutil.copyfile(source_path, temporary)
            os.replace(temporary, destination)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise StorageError("Could not save the stored object.") from exc
        return self._stored_object(key, destination, content_type)

    def open_path(self, key: str) -> Path:
        return safe_join(self.root, key)

    def public_url(self, key: str) -> str:
        return f"{self.public_url_prefix}/{normalize_object_key(key)}"

    def delete(self, key: str) -> None:
        try:
            self.open_path(key).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("Could not delete the stored object.") from exc

    def _stored_object(
        self,
        key: str,
        path: Path,
        content_type: str | None,
    ) -> StoredObject:
        normalized_key = normalize_object_key(key)
        return StoredObject(
            key=normalized_key,
            path=str(path),
            url=self.public_url(normalized_key),
            content_type=content_type,
            size_bytes=path.stat().st_size,
        )
