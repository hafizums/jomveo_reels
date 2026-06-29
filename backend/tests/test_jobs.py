from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.application.jobs import registry
from backend.app.core.config import Settings
from backend.app.core.errors import ConfigurationError, ProviderError
from backend.app.db.models import GenerationJob, ProviderRun, utc_now
from backend.app.main import create_app
from backend.app.script_generator import ScriptRequest, ScriptResponse

JOB_CASES = [
    ("/api/jobs/scripts/generate", "script.generate", {}),
    ("/api/jobs/voiceovers/generate", "voiceover.generate", {"text": "Hello world"}),
    (
        "/api/jobs/background-music/generate",
        "background_music.generate",
        {"prompt": "Dark cinematic instrumental music"},
    ),
    (
        "/api/jobs/art-style/generate",
        "art_style.generate",
        {"prompt": "A cinematic mountain landscape", "art_direction": "Dramatic realism"},
    ),
    (
        "/api/jobs/art-style/scenes/generate",
        "scene_sequence.generate",
        {
            "script": "A sufficiently long script for deterministic testing.",
            "art_direction": "Dramatic realism",
        },
    ),
    (
        "/api/jobs/scene-animations/generate",
        "scene_animation.generate",
        {
            "scenes": [
                {
                    "scene_number": 1,
                    "image_url": "https://example.test/image.png",
                    "motion_prompt": "Slow camera push forward",
                }
            ]
        },
    ),
    (
        "/api/jobs/videos/generate",
        "video.generate",
        {"voiceover_url": "https://example.test/voice.mp3"},
    ),
]
EXPECTED_PROGRESS_TOTALS = {
    "scene_sequence.generate": 3,
    "scene_animation.generate": 1,
    "video.generate": 5,
}


class StubResult:
    def __init__(self, kind: str, **extra: Any) -> None:
        self.payload = {"kind": kind, **extra}

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        assert mode == "json"
        return self.payload


def _patch_generators(monkeypatch) -> None:
    def fake_script(api_key: str, payload: ScriptRequest) -> ScriptResponse:
        assert api_key == "worker-only-secret"
        return ScriptResponse(
            **payload.model_dump(),
            title="Test title",
            event_name="Test event",
            script="A deterministic generated script.",
            factual_basis="A deterministic factual basis.",
            raw_output={"mocked": True},
        )

    def provider_result(kind: str):
        def generate(api_key: str, _payload: object) -> StubResult:
            assert api_key == "worker-only-secret"
            extra = {"scene_count": 2} if kind == "scene_sequence" else {}
            return StubResult(kind, **extra)

        return generate

    monkeypatch.setattr(registry, "generate_video_script", fake_script)
    monkeypatch.setattr(registry, "generate_voiceover", provider_result("voiceover"))
    monkeypatch.setattr(
        registry,
        "generate_background_music",
        provider_result("background_music"),
    )
    monkeypatch.setattr(registry, "generate_art_style_image", provider_result("art_style"))
    monkeypatch.setattr(
        registry,
        "generate_scene_sequence",
        provider_result("scene_sequence"),
    )
    monkeypatch.setattr(
        registry,
        "generate_scene_animations",
        provider_result("scene_animation"),
    )
    monkeypatch.setattr(
        registry,
        "generate_video",
        lambda _payload, **_kwargs: StubResult("video"),
    )


@pytest.fixture
def job_app(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, FastAPI]]:
    _patch_generators(monkeypatch)
    settings = Settings(
        _env_file=None,
        app_env="test",
        wavespeed_api_key="worker-only-secret",
        generated_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'jobs.db').as_posix()}",
        queue_backend="inline",
        job_retry_backoff_seconds=0,
        job_stale_after_seconds=1,
    )
    application = create_app(settings)
    with TestClient(application) as client:
        yield client, application


def test_script_job_still_completes_inline(job_app) -> None:
    client, _application = job_app
    accepted = client.post("/api/jobs/scripts/generate", json={}).json()
    job = client.get(accepted["status_url"]).json()

    assert accepted["status"] == "queued"
    assert job["status"] == "completed"
    assert job["result"]["title"] == "Test title"
    assert job["attempt_count"] == 1
    assert job["max_attempts"] == 3
    assert job["next_retry_at"] is None


@pytest.mark.parametrize(("route", "job_type", "payload"), JOB_CASES[1:])
def test_remaining_generation_jobs_complete_with_mocked_generators(
    job_app,
    route: str,
    job_type: str,
    payload: dict[str, Any],
) -> None:
    client, _application = job_app
    response = client.post(route, json=payload)

    assert response.status_code == 200
    accepted = response.json()
    assert accepted["type"] == job_type
    job = client.get(accepted["status_url"]).json()
    assert job["status"] == "completed"
    assert job["progress_current"] == job["progress_total"]
    assert job["progress_total"] == EXPECTED_PROGRESS_TOTALS.get(job_type, 1)
    assert job["result"] is not None


@pytest.mark.parametrize(("route", "job_type", "payload"), JOB_CASES)
def test_all_job_routes_support_type_scoped_idempotency(
    job_app,
    route: str,
    job_type: str,
    payload: dict[str, Any],
) -> None:
    client, _application = job_app
    headers = {"Idempotency-Key": f"same-{job_type}"}

    first = client.post(route, json=payload, headers=headers)
    second = client.post(route, json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["job_id"] == second.json()["job_id"]


def test_job_input_and_provider_summary_do_not_store_api_key(job_app) -> None:
    client, application = job_app
    created_ids = [
        client.post(route, json=payload).json()["job_id"] for route, _, payload in JOB_CASES
    ]

    with application.state.session_factory() as session:
        jobs = list(session.scalars(select(GenerationJob).where(GenerationJob.id.in_(created_ids))))
        assert len(jobs) == len(JOB_CASES)
        for job in jobs:
            assert "api_key" not in job.input_json
            assert "worker-only-secret" not in str(job.input_json)
        provider_runs = list(
            session.scalars(select(ProviderRun).where(ProviderRun.job_id.in_(created_ids)))
        )
        assert len(provider_runs) == len(JOB_CASES)
        for provider_run in provider_runs:
            assert set(provider_run.request_summary_json or {}) <= {"job_type", "model"}
            assert "worker-only-secret" not in str(provider_run.request_summary_json)


def test_retryable_failure_increments_attempt_and_waits_for_recovery(job_app, monkeypatch) -> None:
    client, _application = job_app

    def fail_generation(_api_key: str, _payload: ScriptRequest) -> ScriptResponse:
        raise ProviderError("Provider temporarily unavailable.")

    monkeypatch.setattr(registry, "generate_video_script", fail_generation)
    accepted = client.post("/api/jobs/scripts/generate", json={}).json()
    job = client.get(accepted["status_url"]).json()

    assert job["status"] == "retrying"
    assert job["attempt_count"] == 1
    assert job["next_retry_at"] is not None
    assert job["error"] == {
        "code": "provider_error",
        "message": "Provider temporarily unavailable.",
    }


def test_exhausted_retryable_failure_becomes_failed(job_app, monkeypatch) -> None:
    client, application = job_app
    application.state.settings.job_max_attempts = 1

    def fail_generation(_api_key: str, _payload: ScriptRequest) -> ScriptResponse:
        raise ProviderError("Provider remains unavailable.")

    monkeypatch.setattr(registry, "generate_video_script", fail_generation)
    accepted = client.post("/api/jobs/scripts/generate", json={}).json()
    job = client.get(accepted["status_url"]).json()

    assert job["status"] == "failed"
    assert job["attempt_count"] == 1
    assert job["next_retry_at"] is None


def test_non_retryable_configuration_error_fails_immediately(job_app, monkeypatch) -> None:
    client, _application = job_app

    def fail_generation(_api_key: str, _payload: ScriptRequest) -> ScriptResponse:
        raise ConfigurationError("Worker configuration is invalid.")

    monkeypatch.setattr(registry, "generate_video_script", fail_generation)
    accepted = client.post("/api/jobs/scripts/generate", json={}).json()
    job = client.get(accepted["status_url"]).json()

    assert job["status"] == "failed"
    assert job["attempt_count"] == 1
    assert job["error"]["code"] == "configuration_error"


def test_stale_recovery_requeues_remaining_attempts_and_fails_exhausted(job_app) -> None:
    client, application = job_app
    stale_time = utc_now() - timedelta(minutes=5)
    with application.state.session_factory() as session:
        recoverable = GenerationJob(
            type="script.generate",
            status="running",
            input_json=ScriptRequest().model_dump(mode="json"),
            attempt_count=1,
            max_attempts=3,
            updated_at=stale_time,
            last_heartbeat_at=stale_time,
        )
        exhausted = GenerationJob(
            type="script.generate",
            status="running",
            input_json=ScriptRequest().model_dump(mode="json"),
            attempt_count=3,
            max_attempts=3,
            updated_at=stale_time,
            last_heartbeat_at=stale_time,
        )
        session.add_all([recoverable, exhausted])
        session.commit()
        recoverable_id = recoverable.id
        exhausted_id = exhausted.id

    response = client.post("/api/jobs/recover-stale")

    assert response.status_code == 200
    assert response.json() == {"recovered_stale": 2, "requeued_due": 1}
    assert client.get(f"/api/jobs/{recoverable_id}").json()["status"] == "completed"
    exhausted_job = client.get(f"/api/jobs/{exhausted_id}").json()
    assert exhausted_job["status"] == "failed"
    assert exhausted_job["error"]["code"] == "internal_server_error"


def test_job_can_be_cancelled_before_execution(job_app) -> None:
    client, application = job_app
    with application.state.session_factory() as session:
        job = GenerationJob(
            type="script.generate",
            status="queued",
            input_json=ScriptRequest().model_dump(mode="json"),
            max_attempts=3,
        )
        session.add(job)
        session.commit()
        job_id = job.id

    response = client.post(f"/api/jobs/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json() == {"job_id": job_id, "status": "cancelled"}
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "cancelled"


def test_job_list_includes_every_generation_type(job_app) -> None:
    client, _application = job_app
    for route, _job_type, payload in JOB_CASES:
        client.post(route, json=payload)

    body = client.get("/api/jobs?limit=20").json()
    assert {job["type"] for job in body["jobs"]} == {job_type for _, job_type, _ in JOB_CASES}


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
