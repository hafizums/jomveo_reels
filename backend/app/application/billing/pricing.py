import math
from typing import Any

from pydantic import BaseModel

from backend.app.core.config import Settings


class CostEstimate(BaseModel):
    estimated_credits: int
    pricing_version: str
    details: dict[str, Any]


def estimate_job_cost(
    job_type: str, input_json: dict[str, Any], settings: Settings
) -> CostEstimate:
    credits = {
        "script.generate": 5,
        "voiceover.generate": 20,
        "background_music.generate": 30,
        "art_style.generate": 10,
        "video.generate": 5,
    }.get(job_type, 5)
    details: dict[str, Any] = {"job_type": job_type}
    if job_type == "scene_sequence.generate":
        scene_count = min(10, max(3, math.ceil(int(input_json.get("duration_seconds", 60)) / 7.5)))
        credits = (
            10 + scene_count * 10 + (2 if input_json.get("enable_safety_checker", True) else 0)
        )
        details["estimated_scene_count"] = scene_count
    elif job_type == "scene_animation.generate":
        scenes = input_json.get("scenes") if isinstance(input_json.get("scenes"), list) else []
        credits = sum(30 if int(scene.get("duration_seconds", 5)) >= 8 else 20 for scene in scenes)
        credits = max(20, credits)
        details["scene_count"] = len(scenes)
    return CostEstimate(
        estimated_credits=credits,
        pricing_version=settings.pricing_version,
        details=details,
    )
