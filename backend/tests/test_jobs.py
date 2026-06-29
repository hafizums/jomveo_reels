from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.core.errors import ProviderError
from backend.app.db.models import GenerationJob, ProviderRun
from backend.app.main import create_app
from backend.app.script_generator import ScriptRequest, ScriptResponse


@pytest.fixture
def job_app(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, FastAPI]]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        wavespeed_api_key="worker-only-secret",
        generated_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'jobs.db').as_posix()}",
        queue_backend="inline",
    )

    def fake_generate(api_key: str, payload: ScriptRequest) -> ScriptResponse:
        assert api_key == "worker-only-secret"
        return ScriptResponse(
            **payload.model_dump(),
            title="Test title",
            event_name="Test event",
            script="A deterministic generated script.",
            factual_basis="A deterministic factual basis.",
            raw_output={"mocked": True},
        )

    monkeypatch.setattr(
        "backend.app.application.jobs.registry.generate_video_script",
        fake_generate,
    )
    application = create_app(settings)
    with TestClient(application) as client:
        yield client, application


def test_script_job_completes_inline_and_can_be_fetched(job_app) -> None:
    client, _application = job_app
    created = client.post("/api/jobs/scripts/generate", json={})

    assert created.status_code == 200
    accepted = created.json()
    assert accepted["type"] == "script.generate"
    assert accepted["status"] == "queued"
    assert accepted["status_url"] == f"/api/jobs/{accepted['job_id']}"

    fetched = client.get(accepted["status_url"])
    assert fetched.status_code == 200
    job = fetched.json()
    assert job["status"] == "completed"
    assert job["progress_current"] == 1
    assert job["progress_total"] == 1
    assert job["result"]["title"] == "Test title"
    assert job["error"] is None
    assert job["started_at"] is not None
    assert job["completed_at"] is not None


def test_job_input_does_not_store_api_key(job_app) -> None:
    client, application = job_app
    created = client.post("/api/jobs/scripts/generate", json={}).json()

    with application.state.session_factory() as session:
        job = session.get(GenerationJob, created["job_id"])
        assert job is not None
        assert "api_key" not in job.input_json
        assert "worker-only-secret" not in str(job.input_json)
        provider_run = session.scalars(
            select(ProviderRun).where(ProviderRun.job_id == job.id)
        ).one()
        assert provider_run.request_summary_json == {"job_type": "script.generate"}


def test_failed_job_stores_safe_provider_error(job_app, monkeypatch) -> None:
    client, _application = job_app

    def fail_generation(_api_key: str, _payload: ScriptRequest) -> ScriptResponse:
        raise ProviderError("Provider temporarily unavailable.")

    monkeypatch.setattr(
        "backend.app.application.jobs.registry.generate_video_script",
        fail_generation,
    )
    created = client.post("/api/jobs/scripts/generate", json={}).json()
    job = client.get(created["status_url"]).json()

    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["error"] == {
        "code": "provider_error",
        "message": "Provider temporarily unavailable.",
    }


def test_missing_job_uses_consistent_error_response(job_app) -> None:
    client, _application = job_app
    response = client.get(
        "/api/jobs/missing-job",
        headers={"X-Request-ID": "missing-job-test"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "job_not_found",
            "message": "Job missing-job was not found.",
            "request_id": "missing-job-test",
        }
    }


def test_recent_jobs_are_listed(job_app) -> None:
    client, _application = job_app
    first = client.post("/api/jobs/scripts/generate", json={}).json()
    second = client.post("/api/jobs/scripts/generate", json={}).json()

    response = client.get("/api/jobs?limit=1")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["jobs"][0]["job_id"] in {first["job_id"], second["job_id"]}


def test_idempotency_key_returns_existing_job(job_app) -> None:
    client, _application = job_app
    headers = {"Idempotency-Key": "same-script-request"}

    first = client.post("/api/jobs/scripts/generate", json={}, headers=headers)
    second = client.post("/api/jobs/scripts/generate", json={}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["job_id"] == second.json()["job_id"]
    assert client.get("/api/jobs").json()["count"] == 1
