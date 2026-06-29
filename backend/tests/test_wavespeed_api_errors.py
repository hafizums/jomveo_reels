import httpx
import pytest
from fastapi import HTTPException

from backend.app.core.errors import (
    ProviderAuthError,
    ProviderBadResponseError,
    ProviderForbiddenError,
    ProviderTimeoutError,
)
from backend.app.wavespeed_api import poll_prediction, submit_prediction


def _client_for(response: httpx.Response) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda request: response))


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [(401, ProviderAuthError), (403, ProviderForbiddenError)],
)
def test_submit_maps_auth_errors(status_code, error_type) -> None:
    response = httpx.Response(status_code, request=httpx.Request("POST", "https://example.test"))
    with _client_for(response) as client, pytest.raises(error_type) as raised:
        submit_prediction(client, "secret", "model", {})

    assert not isinstance(raised.value, HTTPException)


def test_submit_maps_missing_data_to_bad_response() -> None:
    response = httpx.Response(
        200,
        json={"unexpected": True},
        request=httpx.Request("POST", "https://example.test"),
    )
    with _client_for(response) as client, pytest.raises(ProviderBadResponseError):
        submit_prediction(client, "secret", "model", {})


def test_submit_maps_transport_timeout() -> None:
    def timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ProviderTimeoutError) as raised:
            submit_prediction(client, "secret", "model", {})

    assert not isinstance(raised.value, HTTPException)


def test_poll_maps_prediction_timeout(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.wavespeed_api.POLL_TIMEOUT_SECONDS", 0)
    with _client_for(httpx.Response(200, json={"data": {"status": "processing"}})) as client:
        with pytest.raises(ProviderTimeoutError):
            poll_prediction(
                client, "secret", "https://example.test/status", "Generation timed out."
            )
