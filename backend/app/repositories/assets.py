from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Asset


class AssetRepository:
    def __init__(self, session: Session):
        self.session = session

    def for_project(self, project_id: str):
        return list(
            self.session.scalars(
                select(Asset)
                .where(Asset.project_id == project_id)
                .order_by(Asset.created_at.desc())
            )
        )

    def for_job(self, job_id: str):
        return list(
            self.session.scalars(
                select(Asset).where(Asset.job_id == job_id).order_by(Asset.created_at)
            )
        )

    def get(self, asset_id: str):
        return self.session.get(Asset, asset_id)

    def exists(self, job_id: str, url: str):
        return (
            self.session.scalar(select(Asset.id).where(Asset.job_id == job_id, Asset.url == url))
            is not None
        )
