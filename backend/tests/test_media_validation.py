from io import BytesIO

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from backend.app.core.errors import (
    MediaProcessingError,
    MediaValidationError,
    UploadValidationError,
)
from backend.app.media.probe import probe_media
from backend.app.media.validation import validate_magic_bytes, validate_upload_file


@pytest.mark.parametrize(
    ("content_type", "data"),
    [
        ("image/png", b"\x89PNG\r\n\x1a\nrest"),
        ("image/jpeg", b"\xff\xd8\xffrest"),
        ("image/webp", b"RIFF\x04\x00\x00\x00WEBPrest"),
    ],
)
def test_image_magic_bytes_are_accepted(content_type: str, data: bytes) -> None:
    validate_magic_bytes(data, content_type)


def test_invalid_image_magic_bytes_are_rejected() -> None:
    with pytest.raises(MediaValidationError):
        validate_magic_bytes(b"not-an-image", "image/png")


def _upload(filename: str, data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.parametrize(
    ("filename", "content_type", "data"),
    [
        ("image.png", "image/png", b"\x89PNG\r\n\x1a\nrest"),
        ("image.jpg", "image/jpeg", b"\xff\xd8\xffrest"),
        ("image.webp", "image/webp", b"RIFF\x04\x00\x00\x00WEBPrest"),
    ],
)
def test_image_upload_validation_accepts_supported_signatures(
    filename: str,
    content_type: str,
    data: bytes,
) -> None:
    validated = validate_upload_file(
        _upload(filename, data, content_type),
        "image",
        max_bytes=1024,
    )
    assert validated.content_type == content_type


def test_image_upload_validation_rejects_invalid_signature() -> None:
    with pytest.raises(MediaValidationError):
        validate_upload_file(
            _upload("image.png", b"not-a-png", "image/png"),
            "image",
            max_bytes=1024,
        )


def test_oversized_upload_is_rejected() -> None:
    upload = _upload("image.png", b"\x89PNG\r\n\x1a\nrest", "image/png")
    with pytest.raises(UploadValidationError):
        validate_upload_file(upload, "image", max_bytes=4)


@pytest.mark.parametrize(
    ("filename", "content_type", "data"),
    [
        ("captions.srt", "application/x-subrip", b"1\n00:00:00,000 --> 00:00:01,000\nHi"),
        ("captions.vtt", "text/vtt", b"WEBVTT\n\n00:00.000 --> 00:01.000\nHi"),
        ("captions.json", "application/json", b'{"segments": []}'),
        ("captions.txt", "text/plain", b"Plain transcript"),
    ],
)
def test_transcript_upload_extensions_are_accepted(
    filename: str,
    content_type: str,
    data: bytes,
) -> None:
    validated = validate_upload_file(
        _upload(filename, data, content_type),
        "transcript",
        max_bytes=1024,
    )
    assert validated.extension == "." + filename.rsplit(".", 1)[1]


def test_probe_media_reports_missing_ffprobe_safely(tmp_path, monkeypatch) -> None:
    media = tmp_path / "video.mp4"
    media.write_bytes(b"media")
    monkeypatch.setattr("backend.app.media.probe.shutil.which", lambda _name: None)

    with pytest.raises(MediaProcessingError, match="FFprobe"):
        probe_media(media)
