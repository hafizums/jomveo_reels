import logging
import time
from typing import Any

import httpx

from backend.app.core.config import get_settings
from backend.app.core.errors import (
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderError,
    ProviderForbiddenError,
    ProviderTimeoutError,
)

API_BASE_URL = get_settings().wavespeed_api_base_url
POLL_INTERVAL_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 90.0
logger = logging.getLogger(__name__)


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
    try:
        response = client.post(
            f"{API_BASE_URL}/{model}",
            headers=wavespeed_headers(api_key),
            json=payload,
        )
    except httpx.TimeoutException as exc:
        logger.warning("wavespeed_submit_timeout")
        raise ProviderTimeoutError("WaveSpeed request timed out.") from exc
    except httpx.HTTPError as exc:
        logger.warning("wavespeed_submit_transport_error")
        raise ProviderError("Could not connect to WaveSpeed.") from exc

    if response.status_code == 403:
        logger.warning("wavespeed_submit_forbidden", extra={"status_code": 403})
        raise ProviderForbiddenError(build_forbidden_message())

    if response.status_code == 401:
        logger.warning("wavespeed_submit_unauthorized", extra={"status_code": 401})
        raise ProviderAuthError(
            "WaveSpeed returned 401 Unauthorized. Verify WAVESPEED_API_KEY and remove any extra spaces."
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("wavespeed_submit_failed", extra={"status_code": response.status_code})
        raise ProviderError(
            f"WaveSpeed request failed with status {response.status_code}."
        ) from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise ProviderBadResponseError("WaveSpeed submit response was not valid JSON.") from exc
    data = body.get("data")
    if not isinstance(data, dict):
        raise ProviderBadResponseError("WaveSpeed submit response was missing `data`.")

    return data


def poll_prediction(
    client: httpx.Client,
    api_key: str,
    status_url: str,
    timeout_detail: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        try:
            response = client.get(status_url, headers=wavespeed_headers(api_key))
        except httpx.TimeoutException as exc:
            logger.warning("wavespeed_poll_timeout")
            raise ProviderTimeoutError("WaveSpeed polling request timed out.") from exc
        except httpx.HTTPError as exc:
            logger.warning("wavespeed_poll_transport_error")
            raise ProviderError("Could not poll WaveSpeed for results.") from exc

        if response.status_code == 403:
            logger.warning("wavespeed_poll_forbidden", extra={"status_code": 403})
            raise ProviderForbiddenError(build_forbidden_message())

        if response.status_code == 401:
            logger.warning("wavespeed_poll_unauthorized", extra={"status_code": 401})
            raise ProviderAuthError("WaveSpeed returned 401 Unauthorized while polling results.")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("wavespeed_poll_failed", extra={"status_code": response.status_code})
            raise ProviderError(
                f"WaveSpeed polling failed with status {response.status_code}."
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderBadResponseError("WaveSpeed result response was not valid JSON.") from exc
        data = body.get("data")
        if not isinstance(data, dict):
            raise ProviderBadResponseError("WaveSpeed result response was missing `data`.")

        status = data.get("status")
        if status == "completed":
            return data
        if status == "failed":
            provider_message = data.get("error")
            message = (
                provider_message
                if isinstance(provider_message, str) and provider_message
                else "WaveSpeed prediction failed."
            )
            raise ProviderError(message)

        time.sleep(POLL_INTERVAL_SECONDS)

    logger.warning("wavespeed_prediction_timeout")
    raise ProviderTimeoutError(timeout_detail)
