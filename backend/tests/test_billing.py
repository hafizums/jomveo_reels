from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.application.jobs import registry
from backend.app.core.config import Settings
from backend.app.core.errors import ProviderError
from backend.app.db.models import (
    AuditLog,
    CreditAccount,
    CreditTransaction,
    GenerationJob,
    JobCostEstimate,
    Project,
    ProjectQuota,
    ProviderCostRecord,
)
from backend.app.main import create_app
from backend.app.repositories.api_keys import APIKeyRepository
from backend.app.repositories.users import UserRepository
from backend.app.script_generator import ScriptRequest, ScriptResponse

ADMIN_KEY = "billing-admin-key"
USER_KEY = "billing-user-key"
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_KEY}"}
USER_HEADERS = {"X-User-API-Key": USER_KEY}


@pytest.fixture
def billing_app(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, FastAPI]]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        admin_api_keys=[ADMIN_KEY],
        user_auth_enabled=True,
        demo_user_enabled=False,
        billing_enabled=True,
        wavespeed_api_key="worker-test-key",
        generated_root=tmp_path / "generated",
        local_storage_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'billing.db').as_posix()}",
        job_retry_backoff_seconds=0,
    )
    application = create_app(settings)
    with application.state.session_factory() as session:
        user = UserRepository(session).create("billing@example.test", "Billing User")
        APIKeyRepository(session).create(USER_KEY, "billing test", "user", user.id)
        session.commit()

    def fake_script(_api_key: str, payload: ScriptRequest, **_kwargs) -> ScriptResponse:
        return ScriptResponse(
            **payload.model_dump(),
            title="Billing test",
            event_name="Test",
            script="A deterministic billed script.",
            factual_basis="Test fixture.",
            raw_output={"mocked": True},
        )

    monkeypatch.setattr(registry, "generate_video_script", fake_script)
    with TestClient(application) as client:
        yield client, application


def _project(client: TestClient) -> str:
    response = client.post("/api/projects", json={"name": "Billing Project"}, headers=USER_HEADERS)
    assert response.status_code == 201
    return response.json()["id"]


def _top_up(client: TestClient, project_id: str, amount: int = 100) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/billing/top-up",
        json={"amount_credits": amount, "description": "Test credits"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    return response.json()


def test_project_creation_creates_account_quota_and_admin_top_up(billing_app) -> None:
    client, application = billing_app
    project_id = _project(client)

    denied = client.post(
        f"/api/projects/{project_id}/billing/top-up",
        json={"amount_credits": 100},
        headers=USER_HEADERS,
    )
    account = _top_up(client, project_id, 1000)
    transactions = client.get(
        f"/api/projects/{project_id}/billing/transactions", headers=USER_HEADERS
    ).json()

    assert denied.status_code == 403
    assert account["balance_credits"] == 1000
    assert account["available_credits"] == 1000
    assert transactions["transactions"][0]["type"] == "top_up"
    with application.state.session_factory() as session:
        assert session.scalar(select(CreditAccount).where(CreditAccount.project_id == project_id))
        assert session.scalar(select(ProjectQuota).where(ProjectQuota.project_id == project_id))


def test_existing_project_lazily_creates_billing_records(billing_app) -> None:
    client, application = billing_app
    with application.state.session_factory() as session:
        project = Project(name="Legacy", slug="legacy-billing", status="active")
        session.add(project)
        session.commit()
        project_id = project.id

    response = client.get(f"/api/projects/{project_id}/billing", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json()["balance_credits"] == 0


def test_insufficient_credits_blocks_real_project_job(billing_app) -> None:
    client, application = billing_app
    project_id = _project(client)

    response = client.post(
        "/api/jobs/scripts/generate",
        json={},
        headers={**USER_HEADERS, "X-Project-ID": project_id},
    )

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "insufficient_credits"
    with application.state.session_factory() as session:
        assert (
            session.scalar(select(GenerationJob).where(GenerationJob.project_id == project_id))
            is None
        )


def test_demo_billing_can_be_explicitly_enabled(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        demo_user_enabled=True,
        demo_billing_enabled=True,
        billing_enabled=True,
        generated_root=tmp_path / "generated",
        local_storage_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'demo-billing.db').as_posix()}",
    )

    response = TestClient(create_app(settings)).post("/api/jobs/scripts/generate", json={})

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "insufficient_credits"


def test_successful_job_reserves_consumes_and_records_provider_cost(billing_app) -> None:
    client, application = billing_app
    project_id = _project(client)
    _top_up(client, project_id, 100)

    response = client.post(
        "/api/jobs/scripts/generate",
        json={},
        headers={**USER_HEADERS, "X-Project-ID": project_id},
    )

    assert response.status_code == 200
    with application.state.session_factory() as session:
        job = session.get(GenerationJob, response.json()["job_id"])
        account = session.scalar(
            select(CreditAccount).where(CreditAccount.project_id == project_id)
        )
        types = set(session.scalars(select(CreditTransaction.type)))
        assert job is not None and job.billing_status == "consumed"
        assert job.estimated_credits == 5
        assert account is not None and account.balance_credits == 95
        assert account.reserved_credits == 0
        assert {"reserve", "consume_reserved"} <= types
        assert session.scalar(select(JobCostEstimate).where(JobCostEstimate.job_id == job.id))
        assert session.scalar(select(ProviderCostRecord).where(ProviderCostRecord.job_id == job.id))


def test_retry_keeps_single_reservation_and_cancel_releases_it(billing_app, monkeypatch) -> None:
    client, application = billing_app
    project_id = _project(client)
    _top_up(client, project_id, 100)

    def fail(*_args, **_kwargs):
        raise ProviderError("Safe provider failure.")

    monkeypatch.setattr(registry, "generate_video_script", fail)
    headers = {
        **USER_HEADERS,
        "X-Project-ID": project_id,
        "Idempotency-Key": "one-reservation",
    }
    first = client.post("/api/jobs/scripts/generate", json={}, headers=headers)
    second = client.post("/api/jobs/scripts/generate", json={}, headers=headers)

    assert first.json()["job_id"] == second.json()["job_id"]
    with application.state.session_factory() as session:
        account = session.scalar(
            select(CreditAccount).where(CreditAccount.project_id == project_id)
        )
        reserves = list(
            session.scalars(select(CreditTransaction).where(CreditTransaction.type == "reserve"))
        )
        assert account is not None and account.reserved_credits == 5
        assert len(reserves) == 1

    cancelled = client.post(f"/api/jobs/{first.json()['job_id']}/cancel", headers=ADMIN_HEADERS)
    assert cancelled.status_code == 200
    with application.state.session_factory() as session:
        job = session.get(GenerationJob, first.json()["job_id"])
        account = session.scalar(
            select(CreditAccount).where(CreditAccount.project_id == project_id)
        )
        assert job is not None and job.billing_status == "released"
        assert account is not None and account.reserved_credits == 0


def test_exhausted_failure_releases_reserved_credits(billing_app, monkeypatch) -> None:
    client, application = billing_app
    application.state.settings.job_max_attempts = 1
    project_id = _project(client)
    _top_up(client, project_id, 100)

    def fail(*_args, **_kwargs):
        raise ProviderError("Safe provider failure.")

    monkeypatch.setattr(registry, "generate_video_script", fail)
    response = client.post(
        "/api/jobs/scripts/generate",
        json={},
        headers={**USER_HEADERS, "X-Project-ID": project_id},
    )

    with application.state.session_factory() as session:
        job = session.get(GenerationJob, response.json()["job_id"])
        account = session.scalar(
            select(CreditAccount).where(CreditAccount.project_id == project_id)
        )
        assert job is not None and job.status == "failed"
        assert job.billing_status == "released"
        assert account is not None and account.reserved_credits == 0


def test_quota_update_blocks_job_and_writes_safe_audit(billing_app) -> None:
    client, application = billing_app
    project_id = _project(client)
    _top_up(client, project_id, 100)
    updated = client.patch(
        f"/api/projects/{project_id}/quotas",
        json={"daily_job_limit": 0},
        headers=ADMIN_HEADERS,
    )
    rejected = client.post(
        "/api/jobs/scripts/generate",
        json={"topic": "a full prompt must not enter billing audit"},
        headers={**USER_HEADERS, "X-Project-ID": project_id},
    )

    assert updated.status_code == 200
    assert rejected.status_code == 429
    with application.state.session_factory() as session:
        audits = list(session.scalars(select(AuditLog)))
        serialized = str([entry.metadata_json for entry in audits])
        assert "quota_updated" in {entry.action for entry in audits}
        assert USER_KEY not in serialized
        assert "full prompt" not in serialized
