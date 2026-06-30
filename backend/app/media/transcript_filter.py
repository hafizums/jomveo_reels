import re
from pathlib import Path

WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
BLOCK_SEPARATOR = re.compile(r"\r?\n\s*\r?\n")


def _normalized_words(value: str) -> list[str]:
    return WORD_PATTERN.findall(value.casefold())


def _cue_text(block: str) -> str:
    lines = block.splitlines()
    timestamp_index = next((index for index, line in enumerate(lines) if "-->" in line), -1)
    if timestamp_index < 0:
        return ""
    return " ".join(lines[timestamp_index + 1 :]).strip()


def _matches_reference(cue: str, reference: str, reference_words: set[str]) -> bool:
    cue_words = _normalized_words(cue)
    if not cue_words:
        return False
    normalized_cue = " ".join(cue_words)
    if normalized_cue in reference:
        return True
    matched_words = sum(word in reference_words for word in cue_words)
    return matched_words / len(cue_words) >= 0.6


def filter_trailing_hallucinated_cues(
    transcript_path: Path,
    transcript_format: str,
    reference_script: str,
) -> int:
    if transcript_format not in {"srt", "vtt"} or not reference_script.strip():
        return 0

    transcript = transcript_path.read_text(encoding="utf-8")
    blocks = BLOCK_SEPARATOR.split(transcript.strip())
    normalized_reference_words = _normalized_words(reference_script)
    if not normalized_reference_words:
        return 0
    normalized_reference = " ".join(normalized_reference_words)
    reference_word_set = set(normalized_reference_words)

    cues = [(index, cue) for index, block in enumerate(blocks) if (cue := _cue_text(block))]
    matching_indices = [
        index
        for index, cue in cues
        if _matches_reference(cue, normalized_reference, reference_word_set)
    ]
    if not matching_indices:
        return 0

    last_matching_index = max(matching_indices)
    removable_indices = {
        index
        for index, cue in cues
        if index > last_matching_index
        and not _matches_reference(cue, normalized_reference, reference_word_set)
    }
    if not removable_indices:
        return 0

    filtered = [block for index, block in enumerate(blocks) if index not in removable_indices]
    transcript_path.write_text("\n\n".join(filtered).rstrip() + "\n", encoding="utf-8")
    return len(removable_indices)
