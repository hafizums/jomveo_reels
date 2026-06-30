import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import APIKey, User, utc_now


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class APIKeyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        raw_key: str,
        name: str,
        role: str,
        user_id: str | None = None,
    ) -> APIKey:
        record = APIKey(
            user_id=user_id,
            name=name,
            key_hash=hash_api_key(raw_key),
            key_prefix=raw_key[:8],
            role=role,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def authenticate(self, raw_key: str) -> tuple[APIKey, User | None] | None:
        digest = hash_api_key(raw_key)
        record = self.session.scalar(
            select(APIKey).where(APIKey.key_hash == digest, APIKey.status == "active")
        )
        if record is None or record.revoked_at is not None:
            return None
        if not secrets.compare_digest(digest, record.key_hash):
            return None
        record.last_used_at = utc_now()
        user = self.session.get(User, record.user_id) if record.user_id else None
        return record, user
