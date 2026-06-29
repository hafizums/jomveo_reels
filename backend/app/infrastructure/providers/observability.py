from datetime import datetime
from typing import Any


def safe_provider_request_summary(
    job_type: str,
    model: str | None,
    provider_mode: str,
) -> dict[str, Any]:
    return {
        "job_type": job_type,
        "model": model,
        "provider_mode": provider_mode,
    }


def safe_provider_response_summary(response: dict[str, Any]) -> dict[str, Any]:
    outputs: Any = response.get("outputs")
    raw_output = response.get("raw_output")
    if outputs is None and isinstance(raw_output, dict):
        outputs = raw_output.get("outputs")
    if outputs is None:
        outputs = response.get("scenes") or response.get("audio_urls")
    if outputs is None and any(
        response.get(key) for key in ("image_url", "audio_url", "output_url")
    ):
        outputs = [True]
    if isinstance(outputs, list):
        output_count = len(outputs)
    elif outputs is None:
        output_count = 0
    else:
        output_count = 1
    return {
        "result_available": bool(response),
        "output_count": output_count,
    }


def duration_ms(start: datetime, end: datetime) -> int:
    if start.tzinfo is None and end.tzinfo is not None:
        start = start.replace(tzinfo=end.tzinfo)
    elif end.tzinfo is None and start.tzinfo is not None:
        end = end.replace(tzinfo=start.tzinfo)
    return max(0, round((end - start).total_seconds() * 1000))
