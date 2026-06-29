from pathlib import Path

import pytest

from backend.app.core.errors import UnsafePathError
from backend.app.storage.local import LocalStorageBackend
from backend.app.storage.paths import make_object_key, safe_join, sanitize_filename


@pytest.mark.parametrize(
    "key",
    ["../secret.txt", "safe/../../secret.txt", "/absolute.txt", r"C:\secret.txt"],
)
def test_safe_join_rejects_unsafe_paths(tmp_path: Path, key: str) -> None:
    with pytest.raises(UnsafePathError):
        safe_join(tmp_path, key)


def test_filename_sanitizer_removes_path_and_unsafe_characters() -> None:
    assert sanitize_filename("../../my evil<script>.PNG") == "my-evil-script.png"
    assert sanitize_filename("..", fallback="upload") == "upload"


def test_make_object_key_normalizes_safe_filename() -> None:
    assert make_object_key("uploads/videos", "../My Clip!.mp4") == "uploads/videos/My-Clip.mp4"


def test_local_storage_saves_and_serves_safe_objects(tmp_path: Path) -> None:
    storage = LocalStorageBackend(tmp_path, "/generated")
    stored = storage.save_bytes("images/test.png", b"png-data", "image/png")

    assert Path(stored.path).read_bytes() == b"png-data"
    assert stored.url == "/generated/images/test.png"
    assert stored.size_bytes == 8

    storage.delete(stored.key)
    assert not Path(stored.path).exists()


def test_local_storage_prevents_traversal(tmp_path: Path) -> None:
    storage = LocalStorageBackend(tmp_path)
    with pytest.raises(UnsafePathError):
        storage.save_bytes("../outside.txt", b"blocked")
