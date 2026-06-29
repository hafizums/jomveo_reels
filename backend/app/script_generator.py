import json
from textwrap import dedent
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.app.core.config import get_settings

LLM_BASE_URL = get_settings().wavespeed_llm_base_url
DEFAULT_SCRIPT_MODEL = "openai/gpt-5.1"
DEFAULT_SCRIPT_STYLE = "Storytelling"
DEFAULT_SCRIPT_DURATION_SECONDS = 60
DEFAULT_SCRIPT_TRUTH_MODE = "factual"
DEFAULT_SCRIPT_LANGUAGE = "English"
DEFAULT_SCRIPT_NICHE = (
    "Storytelling format. True historical horror stories and dark real-world events "
    "with psychological terror elements. Focus on elite military operatives, legendary "
    "snipers, assassins, Cold War stories that inspired films, nuclear disasters, "
    "radiation poisoning, toxic waste cover-ups, serial killers, psychiatric escapees, "
    "mass murderers, unexplained disappearances, Cold War espionage, containment "
    "breaches, military black ops, extreme survival cases, cult leaders, plane crashes, "
    "maritime disasters, abandoned research stations, and lost expeditions. Exclude "
    "fictional monsters and supernatural entities. Focus on factual human evil, natural "
    "predators, scientific disasters, and documented historical events that feel too "
    "disturbing to be true."
)

SCRIPT_SYSTEM_PROMPT = dedent(
    """
    You write scripts for short-form videos with deliberately slow narration.

    The user will specify a truth mode. You must obey it precisely.

    Truth mode rules:
    - factual: Every script must be based on a real, documented historical event or a real documented person. Never invent crimes, disasters, conspiracies, or victims. Never use fictional monsters, supernatural explanations, creepypasta, or paranormal claims as fact. If a detail is disputed, phrase it carefully.
    - mythology: You may retell myths, legends, and classical stories, but you must frame them clearly as mythology, legend, or traditional storytelling, not as verified history.
    - inspirational: You may write reflective or motivational scripts, but do not fabricate quotes, fake statistics, or pretend a lesson is sourced from a real event unless it actually is.

    Writing goals:
    - Use a gripping, spoken-word storytelling tone.
    - Make the pacing feel like a viral short video.
    - Keep the script within the exact spoken-word range supplied by the user.
    - Use short paragraphs or single-sentence lines, similar to the user's example.
    - End on a chilling factual note rather than a moral lecture.

    Output a JSON object with exactly these keys:
    title
    event_name
    script
    factual_basis

    Rules for the JSON fields:
    - title: a short punchy title
    - event_name: the real event, person, or case the script is about
    - script: the full script with paragraph breaks preserved
    - factual_basis: one or two sentences explaining why this is a real documented case
    """
).strip()


class ScriptRequest(BaseModel):
    niche: str = Field(default=DEFAULT_SCRIPT_NICHE, min_length=20, max_length=4000)
    style: str = Field(default=DEFAULT_SCRIPT_STYLE, min_length=1, max_length=80)
    topic_hint: str = Field(default="", max_length=200)
    duration_seconds: int = Field(default=DEFAULT_SCRIPT_DURATION_SECONDS, ge=30, le=90)
    model: str = Field(default=DEFAULT_SCRIPT_MODEL, min_length=1, max_length=120)
    truth_mode: str = Field(default=DEFAULT_SCRIPT_TRUTH_MODE, min_length=3, max_length=40)
    language: str = Field(default=DEFAULT_SCRIPT_LANGUAGE, min_length=2, max_length=40)


class ScriptResponse(BaseModel):
    niche: str
    style: str
    topic_hint: str
    duration_seconds: int
    model: str
    truth_mode: str
    language: str
    title: str
    event_name: str
    script: str
    factual_basis: str
    raw_output: dict[str, Any]


def _wavespeed_llm_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _slow_narration_word_range(duration_seconds: int) -> tuple[int, int]:
    """Allow about 84–99 spoken words per minute for a slow, dramatic delivery."""
    minimum = round(duration_seconds * 1.4)
    maximum = round(duration_seconds * 1.65)
    return minimum, maximum


def _build_script_prompt(payload: ScriptRequest) -> str:
    minimum_words, maximum_words = _slow_narration_word_range(payload.duration_seconds)
    topic_line = (
        f"Prefer this topic if it is real and well documented: {payload.topic_hint}."
        if payload.topic_hint
        else "Choose the strongest real historical case that fits the niche."
    )

    return dedent(
        f"""
        Create a {payload.duration_seconds}-second video script in {payload.style} format.

        Truth mode:
        {payload.truth_mode}

        Output language:
        {payload.language}

        Niche:
        {payload.niche}

        Topic guidance:
        {topic_line}

        Additional requirements:
        - The narrator speaks slowly and dramatically.
        - The script field must contain between {minimum_words} and {maximum_words} spoken words.
        - {maximum_words} words is a hard maximum. Count only the words in the script field.
        - Follow the truth mode exactly.
        - Do not present rumors or internet myths as confirmed facts when truth mode is factual.
        - Write the title, event_name, script, and factual_basis in {payload.language}.
        - Use a strong hook in the opening line.
        - Keep the language vivid but factual.
        - Write in short paragraphs, like a narration script for Shorts or Reels.
        - Do not include bullets, scene headings, hashtags, citations, or emojis.
        - Make the ending land hard, but stay factual.
        """
    ).strip()


def _parse_script_content(content: str) -> dict[str, str]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "title": "Untitled Script",
            "event_name": "Unspecified real event",
            "script": content.strip(),
            "factual_basis": "The model returned plain text instead of JSON. Review the factual claims before publishing.",
        }

    return {
        "title": str(parsed.get("title", "Untitled Script")).strip(),
        "event_name": str(parsed.get("event_name", "Unspecified real event")).strip(),
        "script": str(parsed.get("script", "")).strip(),
        "factual_basis": str(parsed.get("factual_basis", "")).strip(),
    }


def _extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise HTTPException(
            status_code=502, detail="WaveSpeed LLM response did not include any choices."
        )

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise HTTPException(
            status_code=502, detail="WaveSpeed LLM response did not include a message."
        )

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(
            status_code=502, detail="WaveSpeed LLM response did not include text content."
        )

    return content


def generate_video_script(api_key: str, payload: ScriptRequest) -> ScriptResponse:
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=_wavespeed_llm_headers(api_key),
            json={
                "model": payload.model,
                "temperature": 0.9,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SCRIPT_SYSTEM_PROMPT},
                    {"role": "user", "content": _build_script_prompt(payload)},
                ],
            },
        )

    if response.status_code == 403:
        raise HTTPException(
            status_code=502,
            detail=(
                "WaveSpeed LLM returned 403 Forbidden. Check that your WaveSpeed API key is active, "
                "the account is allowed to use the LLM API, and the model is available to your account."
            ),
        )

    if response.status_code == 401:
        raise HTTPException(
            status_code=502,
            detail="WaveSpeed LLM returned 401 Unauthorized. Verify WAVESPEED_API_KEY and remove any extra spaces.",
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"WaveSpeed LLM request failed: {exc}") from exc

    body = response.json()
    content = _extract_message_content(body)
    parsed = _parse_script_content(content)

    if not parsed["script"]:
        raise HTTPException(status_code=502, detail="WaveSpeed LLM returned an empty script.")

    return ScriptResponse(
        niche=payload.niche,
        style=payload.style,
        topic_hint=payload.topic_hint,
        duration_seconds=payload.duration_seconds,
        model=payload.model,
        truth_mode=payload.truth_mode,
        language=payload.language,
        title=parsed["title"],
        event_name=parsed["event_name"],
        script=parsed["script"],
        factual_basis=parsed["factual_basis"],
        raw_output=body,
    )
