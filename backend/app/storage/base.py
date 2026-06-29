from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class StoredObject(BaseModel):
    key: str
    path: str
    url: str
    content_type: str | None = None
    size_bytes: int


class StorageBackend(Protocol):
    def save_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObject: ...

    def save_file(
        self,
        key: str,
        source_path: Path,
        content_type: str | None = None,
    ) -> StoredObject: ...

    def open_path(self, key: str) -> Path: ...

    def public_url(self, key: str) -> str: ...

    def delete(self, key: str) -> None: ...
