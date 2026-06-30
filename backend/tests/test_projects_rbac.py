from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.application.jobs import registry
from backend.app.core.config import Settings
from backend.app.db.models import (
    APIKey,
    AuditLog,
    GenerationJob,
    Project,
    ProjectMember,
    User,
)
from backend.app.main import create_app
from backend.app.repositories.api_keys import APIKeyRepository, hash_api_key
from backend.app.repositories.users import UserRepository
from backend.app.script_generator import ScriptRequest, ScriptResponse

ADMIN_KEY = "milestone-eight-admin-key"
USER_KEYS = {
    "owner": "owner-raw-api-key",
    "project_admin": "project-admin-raw-key",
    "editor": "editor-raw-api-key",
    "viewer": "viewer-raw-api-key",
    "unrelated": "unrelated-raw-api-key",
}


@pytest.fixture
def ownership_app(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, FastAPI, dict[str, User]]]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        admin_api_keys=[ADMIN_KEY],
        user_auth_enabled=True,
        demo_user_enabled=False,
        billing_enabled=False,
        wavespeed_api_key="worker-test-key",
        generated_root=tmp_path / "generated",
        local_storage_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'ownership.db').as_posix()}",
        queue_backend="inline",
    )
    application = create_app(settings)
    users: dict[str, User] = {}
    with application.state.session_factory() as session:
        user_repository = UserRepository(session)
        key_repository = APIKeyRepository(session)
        for name, raw_key in USER_KEYS.items():
            user = user_repository.create(f"{name}@example.test", name.replace("_", " ").title())
            key_repository.create(raw_key, f"{name} test key", "user", user.id)
            users[name] = user
        session.commit()

    def fake_script(_api_key: str, payload: ScriptRequest, **_kwargs) -> ScriptResponse:
        return ScriptResponse(
            **payload.model_dump(),
            title="Scoped job",
            event_name="Test",
            script="A safe deterministic script.",
            factual_basis="Test fixture.",
            raw_output={"mocked": True},
        )

    monkeypatch.setattr(registry, "generate_video_script", fake_script)
    with TestClient(application) as client:
        yield client, application, users


def _user_headers(name: str, project_id: str | None = None) -> dict[str, str]:
    headers = {"X-User-API-Key": USER_KEYS[name]}
    if project_id:
        headers["X-Project-ID"] = project_id
    return headers


def _create_project(client: TestClient) -> dict:
    response = client.post(
        "/api/projects",
        json={"name": "Owned Project", "description": "RBAC test project"},
        headers=_user_headers("owner"),
    )
    assert response.status_code == 201
    return response.json()


def test_api_key_is_hashed_and_resolves_user_principal(ownership_app) -> None:
    client, application, users = ownership_app
    raw_key = USER_KEYS["owner"]

    response = client.get("/api/me", headers=_user_headers("owner"))

    assert response.status_code == 200
    assert response.json()["user_id"] == users["owner"].id
    assert response.json()["role"] == "user"
    with application.state.session_factory() as session:
        record = session.scalar(select(APIKey).where(APIKey.user_id == users["owner"].id))
        assert record is not None
        assert record.key_hash == hash_api_key(raw_key)
        assert raw_key not in record.key_hash
        assert raw_key not in str(record.__dict__)


def test_invalid_user_key_is_rejected_without_token_leak(ownership_app) -> None:
    client, application, _users = ownership_app
    token = "invalid-user-secret-token"

    response = client.get("/api/me", headers={"X-User-API-Key": token})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "auth_forbidden"
    assert token not in response.text
    with application.state.session_factory() as session:
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "api_key_rejected"))
        assert audit is not None
        assert token not in str(audit.__dict__)


def test_demo_identity_and_project_preserve_unauthenticated_mode(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        demo_user_enabled=True,
        generated_root=tmp_path / "generated",
        local_storage_root=tmp_path / "generated",
        database_url=f"sqlite:///{(tmp_path / 'demo.db').as_posix()}",
    )
    application = create_app(settings)

    response = TestClient(application).get("/api/me")

    assert response.status_code == 200
    assert response.json()["email"] == "demo@jomveo.local"
    with application.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "demo@jomveo.local"))
        project = session.scalar(select(Project).where(Project.slug == "demo"))
        assert user is not None
        assert project is not None
        assert session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
                ProjectMember.role == "owner",
            )
        )


def test_project_creation_requires_principal_and_creator_becomes_owner(ownership_app) -> None:
    client, application, users = ownership_app
    denied = client.post("/api/projects", json={"name": "Denied"})
    project = _create_project(client)

    assert denied.status_code == 401
    assert project["created_by_user_id"] == users["owner"].id
    assert project["role"] == "owner"
    with application.state.session_factory() as session:
        membership = session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project["id"],
                ProjectMember.user_id == users["owner"].id,
            )
        )
        assert membership is not None
        assert membership.role == "owner"


def test_project_list_and_updates_are_role_scoped(ownership_app) -> None:
    client, _application, users = ownership_app
    project = _create_project(client)
    project_id = project["id"]
    add = client.post(
        f"/api/projects/{project_id}/members",
        json={"user_id": users["project_admin"].id, "role": "admin"},
        headers=_user_headers("owner"),
    )
    assert add.status_code == 200

    owner_list = client.get("/api/projects", headers=_user_headers("owner")).json()
    unrelated_list = client.get("/api/projects", headers=_user_headers("unrelated")).json()
    updated = client.patch(
        f"/api/projects/{project_id}",
        json={"name": "Updated by project admin"},
        headers=_user_headers("project_admin"),
    )

    assert owner_list["count"] == 1
    assert unrelated_list["count"] == 0
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated by project admin"


def test_member_roles_enforce_project_job_permissions(ownership_app) -> None:
    client, application, users = ownership_app
    project_id = _create_project(client)["id"]
    for name, role in (("editor", "editor"), ("viewer", "viewer")):
        response = client.post(
            f"/api/projects/{project_id}/members",
            json={"user_id": users[name].id, "role": role},
            headers=_user_headers("owner"),
        )
        assert response.status_code == 200

    denied = client.post(
        "/api/jobs/scripts/generate",
        json={},
        headers=_user_headers("viewer", project_id),
    )
    accepted = client.post(
        "/api/jobs/scripts/generate",
        json={},
        headers=_user_headers("editor", project_id),
    )

    assert denied.status_code == 403
    assert accepted.status_code == 200
    job_id = accepted.json()["job_id"]
    with application.state.session_factory() as session:
        job = session.get(GenerationJob, job_id)
        assert job is not None
        assert job.project_id == project_id
        assert job.created_by_user_id == users["editor"].id

    project_jobs = client.get(f"/api/projects/{project_id}/jobs", headers=_user_headers("viewer"))
    unrelated = client.get(f"/api/jobs/{job_id}", headers=_user_headers("unrelated"))
    admin = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {ADMIN_KEY}"})
    assert project_jobs.status_code == 200
    assert project_jobs.json()["count"] == 1
    assert unrelated.status_code == 403
    assert admin.status_code == 200


def test_owner_can_delete_project_and_project_admin_cannot_remove_owner(ownership_app) -> None:
    client, _application, users = ownership_app
    project_id = _create_project(client)["id"]
    client.post(
        f"/api/projects/{project_id}/members",
        json={"user_id": users["project_admin"].id, "role": "admin"},
        headers=_user_headers("owner"),
    )

    denied = client.delete(
        f"/api/projects/{project_id}/members/{users['owner'].id}",
        headers=_user_headers("project_admin"),
    )
    deleted = client.delete(f"/api/projects/{project_id}", headers=_user_headers("owner"))

    assert denied.status_code == 403
    assert deleted.status_code == 204


def test_admin_actions_write_safe_persistent_audit_logs(ownership_app) -> None:
    client, application, users = ownership_app
    project_id = _create_project(client)["id"]
    with application.state.session_factory() as session:
        job = GenerationJob(
            type="script.generate",
            status="queued",
            input_json={"script": "full secret prompt that must not reach audit"},
            max_attempts=3,
            project_id=project_id,
            created_by_user_id=users["owner"].id,
        )
        session.add(job)
        session.commit()
        job_id = job.id

    admin_headers = {"Authorization": f"Bearer {ADMIN_KEY}"}
    assert client.post(f"/api/jobs/{job_id}/cancel", headers=admin_headers).status_code == 200
    assert client.post("/api/jobs/recover-stale", headers=admin_headers).status_code == 200
    assert (
        client.get("/api/provider/wavespeed/status?live=true", headers=admin_headers).status_code
        == 200
    )

    with application.state.session_factory() as session:
        logs = list(session.scalars(select(AuditLog)))
        actions = {entry.action for entry in logs}
        serialized = str(
            [(entry.actor_subject, entry.metadata_json, entry.resource_id) for entry in logs]
        )
        assert {"job_cancelled", "job_recovered_stale", "provider_live_status"} <= actions
        assert ADMIN_KEY not in serialized
        assert "full secret prompt" not in serialized
