import os

import pytest

from backend.app.core.config import Settings
from backend.app.infrastructure.providers.wavespeed.client import extract_first_asset_url
from backend.app.infrastructure.providers.wavespeed.sdk_client import WaveSpeedSDKClient

pytestmark = [
    pytest.mark.live_provider,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_PROVIDER_TESTS") != "1" or not os.getenv("WAVESPEED_API_KEY"),
        reason="requires RUN_LIVE_PROVIDER_TESTS=1 and WAVESPEED_API_KEY",
    ),
]


def test_wavespeed_sdk_generates_one_small_image() -> None:
    settings = Settings(_env_file=None)
    response = WaveSpeedSDKClient(settings).run_model(
        settings.provider_smoke_test_model,
        {
            "prompt": "A single small blue circle centered on a plain white background",
            "size": "1024*1024",
            "enable_safety_checker": True,
        },
        timeout_seconds=settings.provider_smoke_test_timeout_seconds,
    )

    assert extract_first_asset_url(response).startswith(("http://", "https://"))
