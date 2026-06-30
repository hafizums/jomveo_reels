import re
import subprocess

from backend.app.housekeeping.schemas import Finding

ROUTE_RE = re.compile(r"[\"'`](\/api\/[A-Za-z0-9_{}$/.?=&-]+)")
ENV_RE = re.compile(r"\b(?:VITE_)?[A-Z][A-Z0-9_]{2,}\b")
REVIEW_RE = re.compile(
    r"\b(openai/|wavespeed-ai/|google/|mureka-ai/|elevenlabs/|wan-|z-image|nano-banana|gpt-|pricing|credits|retention|expires)\b",
    re.I,
)
MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|known limitation|deferred|future work)\b", re.I)


def finding(severity, category, file, line, message, suggestion, evidence):
    return Finding(severity, category, file, line, message, suggestion, evidence[:240])


def lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []


def documented_routes(text):
    return {m.group(1).split("?")[0] for m in ROUTE_RE.finditer(text)}


def frontend_routes(root):
    routes = set()
    for path in (root / "frontend/src").rglob("*"):
        if path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            for match in ROUTE_RE.finditer("\n".join(lines(path))):
                routes.add(re.sub(r"\$\{[^}]+\}", "{param}", match.group(1).split("?")[0]))
    return routes


def env_keys(path):
    return {
        line.split("=", 1)[0].strip()
        for line in lines(path)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", line)
    }


def scan_text(root):
    out = []
    for path in [
        root / "README.md",
        *list((root / "backend/app").rglob("*.py")),
        *list((root / "frontend/src").rglob("*.js")),
        *list((root / "frontend/src").rglob("*.jsx")),
    ]:
        if "alembic" in path.parts:
            continue
        for number, line in enumerate(lines(path), 1):
            rel = path.relative_to(root).as_posix()
            if REVIEW_RE.search(line):
                out.append(
                    finding(
                        "medium",
                        "provider",
                        rel,
                        number,
                        "Provider/model/pricing information should be manually reviewed.",
                        "Confirm this assumption before release.",
                        line.strip(),
                    )
                )
            if MARKER_RE.search(line):
                out.append(
                    finding(
                        "medium"
                        if any(x in rel for x in ("auth", "billing", "provider"))
                        else "low",
                        "todo",
                        rel,
                        number,
                        "Maintenance marker may be outdated.",
                        "Review or resolve this marker.",
                        line.strip(),
                    )
                )
            if re.search(r"\b20(?:24|25|26)-\d{2}-\d{2}\b|\bMilestone \d+\b", line):
                out.append(
                    finding(
                        "low",
                        "milestone",
                        rel,
                        number,
                        "Hardcoded date or milestone reference may become stale.",
                        "Confirm this historical reference is still useful.",
                        line.strip(),
                    )
                )
            if re.search(r"(?:guaranteed|expires? after)\s+7 days", line, re.I):
                out.append(
                    finding(
                        "medium",
                        "assets",
                        rel,
                        number,
                        "Retention wording sounds guaranteed.",
                        "Use configurable, non-guaranteed retention wording.",
                        line.strip(),
                    )
                )
    return out


def tracked_artifacts(root, tracked=None):
    if tracked is None:
        try:
            tracked = subprocess.run(
                ["git", "ls-files"], cwd=root, text=True, capture_output=True, check=True
            ).stdout.splitlines()
        except (OSError, subprocess.CalledProcessError):
            tracked = []
    pattern = re.compile(
        r"(__pycache__|\.py[co]$|\.pyd$|jomveo\.db$|\.sqlite3?$|backend/generated/|frontend/dist/|(^|/)\.env$)"
    )
    return [
        finding(
            "high",
            "docs",
            p,
            1,
            "Generated or secret artifact is tracked.",
            "Remove it from Git tracking and update .gitignore.",
            p,
        )
        for p in tracked
        if pattern.search(p)
    ]
