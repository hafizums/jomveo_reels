from datetime import datetime

from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    project_id: str | None
    job_id: str | None
    asset_type: str
    provider: str
    storage_type: str
    url: str
    status: str
    expires_at: datetime | None
    download_required: bool
    warning: str | None
    created_at: datetime


class AssetListResponse(BaseModel):
    assets: list[AssetResponse]
    count: int
