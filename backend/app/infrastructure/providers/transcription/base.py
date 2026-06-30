from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class TranscriptionResult:
    transcript_path: Path
    transcript_format: str
    provider: str
    model: str


class TranscriptionProvider(Protocol):
    def transcribe_to_file(
        self,
        input_media_path: Path,
        output_directory: Path,
        *,
        language_hint: str = "",
        prompt: str = "",
        output_format: str = "srt",
    ) -> TranscriptionResult: ...
