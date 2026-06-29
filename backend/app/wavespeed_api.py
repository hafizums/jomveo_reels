import time
from typing import Any

import httpx
from fastapi import HTTPException


API_BASE_URL = "https://api.wavespeed.ai/api/v3"
POLL_INTERVAL_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 90.0


def extract_asset_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value

    if isinstance(value, list):
        for item in value:
            url = extract_asset_url(item)
            if url:
                return url

    if isinstance(value, dict):
        for key in ("url", "image", "output", "src", "path", "audio"):
            url = extract_asset_url(value.get(key))
            if url:
                return url

        for item in value.values():
            url = extract_asset_url(item)
            if url:
                return url

    return None


def normalize_size(size: str) -> str:
    return size.replace("x", "*").replace("X", "*")


def wavespeed_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def build_forbidden_message() -> str:
    return (
        "WaveSpeed returned 403 Forbidden. Per the official auth docs, this usually means "
        "the account or key is not allowed to use the API. Check that your API key is active, "
        "your account has completed at least one top-up, and the account is not suspended."
    )


def submit_prediction(
    client: httpx.Client,
    api_key: str,
    model: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        f"{API_BASE_URL}/{model}",
        headers=wavespeed_headers(api_key),
        json=payload,
    )

    if response.status_code == 403:
        raise HTTPException(status_code=502, detail=build_forbidden_message())

    if response.status_code == 401:
        raise HTTPException(
            status_code=502,
            detail="WaveSpeed returned 401 Unauthorized. Verify WAVESPEED_API_KEY and remove any extra spaces.",
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"WaveSpeed request failed: {exc}",
        ) from exc

    body = response.json()
    data = body.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="WaveSpeed submit response was missing `data`.")

    return data


def poll_prediction(
    client: httpx.Client,
    api_key: str,
    status_url: str,
    timeout_detail: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        response = client.get(status_url, headers=wavespeed_headers(api_key))

        if response.status_code == 403:
            raise HTTPException(status_code=502, detail=build_forbidden_message())

        if response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="WaveSpeed returned 401 Unauthorized while polling results.",
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"WaveSpeed polling failed: {exc}",
            ) from exc

        body = response.json()
        data = body.get("data")
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="WaveSpeed result response was missing `data`.")

        status = data.get("status")
        if status == "completed":
            return data
        if status == "failed":
            raise HTTPException(
                status_code=502,
                detail=data.get("error") or "WaveSpeed prediction failed.",
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise HTTPException(status_code=504, detail=timeout_detail)
