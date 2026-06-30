import json

from backend.app.housekeeping.checks import (
    documented_routes,
    env_keys,
    frontend_routes,
    scan_text,
    tracked_artifacts,
)
from backend.app.housekeeping.outdated_info_audit import render_markdown
from backend.app.housekeeping.schemas import Finding


def test_outputs_render():
    item = Finding("high", "routes", "README.md", 1, "Missing", "Fix", "GET /api/x")
    assert "High: 1" in render_markdown([item])
    assert json.loads(json.dumps({"findings": [item.to_dict()]}))["findings"]


def test_route_and_env_helpers(tmp_path):
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/api.js").write_text('fetch("/api/missing")')
    env = tmp_path / ".env.example"
    env.write_text("KNOWN=true\n")
    assert "/api/documented" in documented_routes("`/api/documented`")
    assert "/api/missing" in frontend_routes(tmp_path)
    assert env_keys(env) == {"KNOWN"}


def test_review_todo_retention_and_artifacts(tmp_path):
    (tmp_path / "backend/app").mkdir(parents=True)
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "README.md").write_text(
        "wavespeed-ai/model\nTODO later\nGuaranteed expires after 7 days"
    )
    findings = scan_text(tmp_path)
    assert {f.category for f in findings} >= {"provider", "todo", "assets"}
    assert tracked_artifacts(tmp_path, ["backend/generated/jomveo.db"])[0].severity == "high"
