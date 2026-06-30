from backend.app.media.transcript_filter import filter_trailing_hallucinated_cues


def test_filter_removes_only_unmatched_trailing_cues(tmp_path) -> None:
    transcript = tmp_path / "captions.srt"
    transcript.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nCerita bermula di Paris.\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nMahkota itu jatuh dalam diam.\n\n"
        "3\n00:00:57,000 --> 00:00:59,000\nSari kata pelajar Mediacorp Pte Ltd\n",
        encoding="utf-8",
    )

    removed = filter_trailing_hallucinated_cues(
        transcript,
        "srt",
        "Cerita bermula di Paris. Mahkota itu akhirnya jatuh dalam diam.",
    )

    filtered = transcript.read_text(encoding="utf-8")
    assert removed == 1
    assert "Cerita bermula" in filtered
    assert "Mahkota" in filtered
    assert "Mediacorp" not in filtered


def test_filter_preserves_transcript_when_no_cue_matches_reference(tmp_path) -> None:
    transcript = tmp_path / "captions.srt"
    original = "1\n00:00:00,000 --> 00:00:02,000\nCompletely different wording.\n"
    transcript.write_text(original, encoding="utf-8")

    removed = filter_trailing_hallucinated_cues(
        transcript, "srt", "A reference script with no matching words."
    )

    assert removed == 0
    assert transcript.read_text(encoding="utf-8") == original
