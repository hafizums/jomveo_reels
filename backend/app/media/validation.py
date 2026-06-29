import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from backend.app.core.errors import MediaValidationError, UploadValidationError

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
AUDIO_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/aac",
}
VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
TRANSCRIPT_CONTENT_TYPES = {
    "text/plain",
    "text/vtt",
    "application/x-subrip",
    "application/json",
}

ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".webp"},
    "audio": {".mp3", ".wav", ".m4a", ".aac"},
    "video": {".mp4", ".webm", ".mov"},
    "transcript": {".srt", ".vtt", ".json", ".txt"},
}

CONTENT_TYPES_BY_KIND = {
    "image": IMAGE_CONTENT_TYPES,
    "audio": AUDIO_CONTENT_TYPES,
    "video": VIDEO_CONTENT_TYPES,
    "transcript": TRANSCRIPT_CONTENT_TYPES,
}

CONTENT_TYPES_BY_EXTENSION = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".m4a": {"audio/mp4"},
    ".aac": {"audio/aac"},
    ".mp4": {"video/mp4"},
    ".webm": {"video/webm"},
    ".mov": {"video/quicktime"},
    ".srt": TRANSCRIPT_CONTENT_TYPES,
    ".vtt": TRANSCRIPT_CONTENT_TYPES,
    ".json": TRANSCRIPT_CONTENT_TYPES,
    ".txt": TRANSCRIPT_CONTENT_TYPES,
}


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content_type: str | None
    size_bytes: int
    extension: str


def normalized_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip().lower() or None


def validate_content_type(content_type: str | None, allowed: set[str]) -> None:
    normalized = normalized_content_type(content_type)
    if normalized is not None and normalized not in allowed:
        raise MediaValidationError(f"Unsupported media content type: {normalized}.")


def _matches_image(data: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


def _matches_audio(data: bytes, content_type: str) -> bool:
    if content_type in {"audio/mpeg", "audio/mp3"}:
        return data.startswith(b"ID3") or (
            len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
        )
    if content_type in {"audio/wav", "audio/x-wav"}:
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE"
    if content_type == "audio/mp4":
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if content_type == "audio/aac":
        return len(data) >= 2 and data[0] == 0xFF and data[1] & 0xF6 == 0xF0
    return False


def _matches_video(data: bytes, content_type: str) -> bool:
    if content_type in {"video/mp4", "video/quicktime"}:
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if content_type == "video/webm":
        return data.startswith(b"\x1aE\xdf\xa3")
    return False


def validate_magic_bytes(data: bytes, content_type: str) -> None:
    normalized = normalized_content_type(content_type)
    if normalized in IMAGE_CONTENT_TYPES and _matches_image(data, normalized):
        return
    if normalized in AUDIO_CONTENT_TYPES and _matches_audio(data, normalized):
        return
    if normalized in VIDEO_CONTENT_TYPES and _matches_video(data, normalized):
        return
    if normalized in TRANSCRIPT_CONTENT_TYPES:
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MediaValidationError("Transcript must be UTF-8 text.") from exc
        if normalized == "application/json":
            try:
                json.loads(decoded)
            except json.JSONDecodeError as exc:
                raise MediaValidationError("Transcript JSON is invalid.") from exc
        return
    raise MediaValidationError("File content does not match its declared media type.")


def content_type_for_extension(extension: str, kind: str) -> str:
    extension = extension.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".mp4": "video/mp4" if kind == "video" else "audio/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".srt": "application/x-subrip",
        ".vtt": "text/vtt",
        ".json": "application/json",
        ".txt": "text/plain",
    }
    try:
        return mapping[extension]
    except KeyError as exc:
        raise MediaValidationError(f"Unsupported {kind} file extension.") from exc


def validate_upload_file(upload: UploadFile, kind: str, max_bytes: int) -> ValidatedUpload:
    if not upload.filename:
        raise UploadValidationError("Uploaded file is missing a filename.")
    extension = Path(upload.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS[kind]:
        raise UploadValidationError(f"Unsupported {kind} upload extension.")

    upload.file.seek(0, 2)
    size_bytes = upload.file.tell()
    upload.file.seek(0)
    if size_bytes > max_bytes:
        raise UploadValidationError(f"Uploaded file exceeds the {max_bytes}-byte limit.")
    if size_bytes == 0:
        raise UploadValidationError("Uploaded file is empty.")

    expected_type = content_type_for_extension(extension, kind)
    declared_type = normalized_content_type(upload.content_type)
    try:
        validate_content_type(declared_type, CONTENT_TYPES_BY_KIND[kind])
        if declared_type and declared_type not in CONTENT_TYPES_BY_EXTENSION[extension]:
            raise UploadValidationError(
                "Uploaded file extension does not match its declared content type."
            )
        magic_type = expected_type if kind == "transcript" else declared_type or expected_type
        validate_magic_bytes(upload.file.read(4096), magic_type)
    finally:
        upload.file.seek(0)
    return ValidatedUpload(
        filename=upload.filename,
        content_type=declared_type or expected_type,
        size_bytes=size_bytes,
        extension=extension,
    )


def validate_media_file(
    path: Path,
    kind: str,
    content_type: str | None = None,
) -> None:
    if not path.is_file():
        raise MediaValidationError("Media file does not exist.")
    extension = path.suffix.lower()
    if extension not in ALLOWED_EXTENSIONS[kind]:
        raise MediaValidationError(f"Unsupported {kind} file extension.")
    expected_type = normalized_content_type(content_type) or content_type_for_extension(
        extension, kind
    )
    validate_content_type(expected_type, CONTENT_TYPES_BY_KIND[kind])
    with path.open("rb") as media_file:
        validate_magic_bytes(media_file.read(4096), expected_type)
