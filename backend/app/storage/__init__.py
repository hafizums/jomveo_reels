"""Storage abstractions and local implementation."""

from backend.app.storage.base import StorageBackend, StoredObject
from backend.app.storage.local import LocalStorageBackend

__all__ = ["LocalStorageBackend", "StorageBackend", "StoredObject"]
