import argparse
import json
import re
from pathlib import Path

from backend.app.housekeeping.checks import (
    documented_routes,
    env_keys,
    finding,
    frontend_routes,
    scan_text,
    tracked_artifacts,
)

SECTIONS = (
    "Persistent generation jobs",
    "Administrative authentication",
    "Users, projects, and job ownership",
    "Project billing and quotas",
    "Temporary provider assets",
    "Frontend workspace dashboard",
    "WaveSpeed provider integration",
)


def run(root: Path):
    from backend.app.main import app

    findings = scan_text(root) + tracked_artifacts(root)
    readme = "\n".join((root / "README.md").read_text(encoding="utf-8").splitlines())
    backend = {path for path in app.openapi()["paths"] if path.startswith("/api")}
    docs = documented_routes(readme)
    for route in sorted(docs - backend):
        findings.append(
            finding(
                "high",
                "routes",
                "README.md",
                1,
                "README documents an unregistered API route.",
                "Update documentation or restore the route.",
                route,
            )
        )
    for route in sorted(frontend_routes(root)):
        normalized = re.sub(r"\{param\}", r"[^/]+", route)
        if not any(re.fullmatch(normalized, b) for b in backend):
            findings.append(
                finding(
                    "high",
                    "frontend",
                    "frontend/src",
                    1,
                    "Frontend calls an unregistered API route.",
                    "Update the client or backend route.",
                    route,
                )
            )
    config = set()
    text = (root / "backend/app/core/config.py").read_text(encoding="utf-8")
    for name in re.findall(r"^    ([a-z][a-z0-9_]*):", text, re.M):
        config.add(name.upper())
    for key in sorted(config - env_keys(root / "backend/.env.example")):
        findings.append(
            finding(
                "high",
                "env",
                "backend/.env.example",
                1,
                "Backend setting is missing from the environment example.",
                "Add the setting with a safe default.",
                key,
            )
        )
    for section in SECTIONS:
        if section not in readme:
            findings.append(
                finding(
                    "medium",
                    "docs",
                    "README.md",
                    1,
                    "Required README section is missing.",
                    "Document the current subsystem.",
                    section,
                )
            )
    return findings


def render_markdown(findings):
    counts = {s: sum(f.severity == s for f in findings) for s in ("high", "medium", "low")}
    body = [
        "# Outdated Information Audit",
        "",
        "Summary:",
        *[f"- {s.title()}: {counts[s]}" for s in counts],
        "",
        "## Findings",
    ]
    for f in findings:
        body += [
            "",
            f"### {f.severity.upper()} — {f.category}",
            f"File: {f.file}:{f.line}",
            f.message,
            f"Suggestion: {f.suggestion}",
            f"Evidence: {f.evidence}",
        ]
    return "\n".join(body)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--format", choices=("markdown", "json"), default="markdown")
    p.add_argument("--fail-on", choices=("high", "medium", "low"))
    a = p.parse_args(argv)
    findings = run(Path(a.root).resolve())
    counts = {s: sum(f.severity == s for f in findings) for s in ("high", "medium", "low")}
    print(
        json.dumps({"summary": counts, "findings": [f.to_dict() for f in findings]}, indent=2)
        if a.format == "json"
        else render_markdown(findings)
    )
    threshold = {"high": 3, "medium": 2, "low": 1}
    return (
        1
        if a.fail_on and any(threshold[f.severity] >= threshold[a.fail_on] for f in findings)
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
