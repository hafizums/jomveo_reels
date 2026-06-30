from datetime import UTC, datetime, timedelta

from backend.app.application.assets.extraction import extract_asset_candidates
from backend.app.application.assets.service import (
    EXPIRED_WARNING,
    TEMP_WARNING,
    AssetService,
    asset_status,
)
from backend.app.core.config import Settings
from backend.app.db.models import Asset


def test_extracts_and_deduplicates_supported_asset_shapes():
    values = extract_asset_candidates(
        {
            "image_url": "https://x/a.png",
            "audio_urls": ["https://x/a.mp3", "https://x/a.mp3"],
            "scenes": [{"image_url": "https://x/b.png", "video_url": "https://x/b.mp4"}],
            "raw_output": {"secret": "no", "outputs": ["https://x/c.mp4"]},
        }
    )
    assert len(values) == 5
    assert {value.asset_type for value in values} == {"image", "audio", "video"}


def test_expiry_status_and_warning():
    settings = Settings(_env_file=None, provider_asset_expiring_soon_hours=24)
    now = datetime.now(UTC)
    asset = Asset(
        id="a",
        asset_type="video",
        provider="wavespeed",
        storage_type="provider_ephemeral",
        url="https://x/a.mp4",
        status="available",
        expires_at=now + timedelta(days=2),
        download_required=True,
        created_at=now,
        updated_at=now,
    )
    assert asset_status(asset, settings, now) == "available"
    asset.expires_at = now + timedelta(hours=12)
    assert asset_status(asset, settings, now) == "expiring_soon"
    asset.expires_at = now
    assert asset_status(asset, settings, now) == "expired"

    class Session:
        pass

    assert AssetService(Session(), settings).response(asset).warning == EXPIRED_WARNING
    asset.expires_at = now + timedelta(days=2)
    assert AssetService(Session(), settings).response(asset).warning == TEMP_WARNING
