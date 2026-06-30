from datetime import UTC, datetime, timedelta

from backend.app.application.assets.extraction import (
    calculate_provider_expires_at,
    extract_asset_candidates,
)
from backend.app.application.assets.schemas import AssetListResponse, AssetResponse
from backend.app.auth.models import AuthenticatedPrincipal
from backend.app.core.config import Settings
from backend.app.db.models import Asset, GenerationJob, ProviderRun, utc_now
from backend.app.repositories.assets import AssetRepository
from backend.app.repositories.audit_logs import AuditLogRepository

TEMP_WARNING = (
    "This file is temporarily hosted by the provider. Download it before the link expires."
)
EXPIRED_WARNING = (
    "This provider-hosted file may have expired. Regenerate the asset if the link no longer works."
)


def asset_status(asset: Asset, settings: Settings, now: datetime | None = None) -> str:
    if asset.expires_at is None:
        return "available"
    now = now or datetime.now(UTC)
    expires = asset.expires_at if asset.expires_at.tzinfo else asset.expires_at.replace(tzinfo=UTC)
    if now >= expires:
        return "expired"
    if now >= expires - timedelta(hours=settings.provider_asset_expiring_soon_hours):
        return "expiring_soon"
    return "available"


class AssetService:
    def __init__(self, session, settings: Settings):
        self.session, self.settings = session, settings

    def register(
        self, job: GenerationJob, provider_run: ProviderRun | None, result: dict
    ) -> list[Asset]:
        repository = AssetRepository(self.session)
        values = []
        for item in extract_asset_candidates(result):
            if repository.exists(job.id, item.url):
                continue
            ephemeral = (
                provider_run is not None
                and provider_run.provider == "wavespeed"
                and not item.url.startswith("/generated/")
            )
            asset = Asset(
                project_id=job.project_id,
                job_id=job.id,
                provider_run_id=provider_run.id if provider_run else None,
                created_by_user_id=job.created_by_user_id,
                asset_type=item.asset_type,
                provider="wavespeed"
                if ephemeral
                else "local"
                if item.url.startswith("/generated/")
                else "external",
                storage_type="provider_ephemeral"
                if ephemeral
                else "local_generated"
                if item.url.startswith("/generated/")
                else "external_url",
                url=item.url,
                status="available",
                expires_at=calculate_provider_expires_at(utc_now(), self.settings)
                if ephemeral
                else None,
                download_required=ephemeral,
                metadata_json={
                    "source_field": item.source_field,
                    "scene_number": item.scene_number,
                    "provider_mode": provider_run.provider_mode if provider_run else None,
                    "model": provider_run.model if provider_run else None,
                },
            )
            self.session.add(asset)
            self.session.flush()
            values.append(asset)
            principal = AuthenticatedPrincipal(
                subject=f"user:{job.created_by_user_id}" if job.created_by_user_id else "system",
                role="user",
                user_id=job.created_by_user_id,
            )
            AuditLogRepository(self.session).record(
                principal,
                "asset_registered",
                "asset",
                asset.id,
                job.project_id,
                {
                    "asset_type": asset.asset_type,
                    "storage_type": asset.storage_type,
                    "status": asset.status,
                },
            )
        return values

    def response(self, asset: Asset) -> AssetResponse:
        status = asset_status(asset, self.settings)
        asset.status = status
        warning = None
        if self.settings.asset_download_warning_enabled and asset.download_required:
            warning = EXPIRED_WARNING if status == "expired" else TEMP_WARNING
        return AssetResponse(
            id=asset.id,
            project_id=asset.project_id,
            job_id=asset.job_id,
            asset_type=asset.asset_type,
            provider=asset.provider,
            storage_type=asset.storage_type,
            url=asset.url,
            status=status,
            expires_at=asset.expires_at,
            download_required=asset.download_required,
            warning=warning,
            created_at=asset.created_at,
        )

    def list_response(self, assets: list[Asset]) -> AssetListResponse:
        values = [self.response(asset) for asset in assets]
        return AssetListResponse(assets=values, count=len(values))
