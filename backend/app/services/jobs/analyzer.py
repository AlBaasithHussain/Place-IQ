"""Structured extraction from a pasted job description.

Primary path (AI): an OpenAI-compatible model is asked for strict JSON and the
result is validated with Pydantic. If validation fails we retry once with a
repair instruction; a second failure surfaces as ``JobAnalysisError``.

Fallback path: if no LLM API key is configured, a transparent rule-based
extractor runs so the feature is fully usable locally. The API response records
which engine produced the result (``llm`` or ``heuristic``).
"""

import json
import re

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.job import JobAnalysisResult
from app.services.jobs.keywords import (
    CLOUD_TECHNOLOGIES,
    DATABASES,
    FRAMEWORKS,
    PROGRAMMING_LANGUAGES,
    SOFT_SKILLS,
    detect,
    detect_tools,
)
from app.services.jobs.llm import LLMClient, LLMError

SYSTEM_PROMPT = (
    "You are an expert technical recruiter. You analyze job descriptions and "
    "reply with ONLY a single valid JSON object — no prose and no markdown. "
    "The object MUST have exactly these keys: job_title (string), "
    "required_skills, preferred_skills, programming_languages, frameworks, "
    "databases, cloud_technologies, tools, soft_skills, "
    "experience_requirements, education_requirements (all arrays of short "
    "strings). Use canonical technology names such as \"Python\", "
    "\"PostgreSQL\", \"AWS\". Put explicitly required skills in "
    "required_skills and explicitly optional / nice-to-have skills in "
    "preferred_skills. Capture years-of-experience statements in "
    "experience_requirements and degree/education statements in "
    "education_requirements. Only include items supported by the text; use "
    "empty arrays when nothing applies. Never return null."
)

REPAIR_INSTRUCTION = (
    "Your previous reply was not valid JSON for the required schema. "
    "Reply again with ONLY the corrected JSON object, no code fences."
)

_EXPERIENCE_RE = re.compile(
    r"\b\d+\s*\+?\s*(?:-|–|to)\s*\d+\s*\+?\s*years?\b"
    r"|\b\d+\s*\+?\s*years?\b"
    r"|\b(?:freshers?|entry[- ]level|new grad(?:uate)?)\b",
    re.IGNORECASE,
)

_EDUCATION_RE = re.compile(
    r"\b(bachelor(?:'s)?|master(?:'s)?|b\.?\s?tech|m\.?\s?tech|b\.?\s?e\b|"
    r"m\.?\s?e\b|b\.?\s?sc|m\.?\s?sc|bca|mca|mba|ph\.?\s?d|degree|"
    r"graduate|graduation|diploma)\b",
    re.IGNORECASE,
)

_TITLE_LABEL_RE = re.compile(
    r"^\s*(?:job\s*title|position|role)\s*[:\-–]\s*(.+)$",
    re.IGNORECASE,
)

_TITLE_WORDS = (
    "engineer",
    "developer",
    "analyst",
    "architect",
    "scientist",
    "designer",
    "manager",
    "intern",
    "consultant",
    "administrator",
    "specialist",
    "lead",
    "programmer",
    "tester",
    "devops",
    "sre",
    "data",
    "full stack",
    "full-stack",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "qa",
)
_TITLE_WORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in _TITLE_WORDS) + r")\b",
    re.IGNORECASE,
)

_PREFERRED_HEADING = re.compile(
    r"^\s*(preferred|nice[- ]to[- ]have|bonus|good[- ]to[- ]have|desired|"
    r"added advantage)\b",
    re.IGNORECASE,
)
_REQUIRED_HEADING = re.compile(
    r"^\s*(required|requirements?|must[- ]have|qualifications?|"
    r"basic qualifications|minimum qualifications|responsibilities|"
    r"what you.?ll need|skills?)\b",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(r"^[\s\-–—•*·]\s*")


class JobAnalysisError(Exception):
    """Raised when the AI cannot produce schema-valid structured data."""


def _user_prompt(text: str) -> str:
    return f"Analyze this job description:\n\n{text}"


def _strip_code_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[A-Za-z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    return text.strip()


def _validate(content: str) -> JobAnalysisResult:
    try:
        data = json.loads(_strip_code_fences(content))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("LLM JSON must be an object")
    try:
        return JobAnalysisResult.model_validate(data)
    except ValidationError as exc:
        raise ValueError("JSON does not match the required schema") from exc


def analyze_with_llm(text: str) -> JobAnalysisResult:
    """Ask the configured LLM for JSON, validate it, retry once on failure."""
    try:
        client = LLMClient(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        try:
            return _validate(client.complete_json(SYSTEM_PROMPT, _user_prompt(text)))
        except ValueError:
            repair_prompt = _user_prompt(text) + "\n\n" + REPAIR_INSTRUCTION
            try:
                return _validate(client.complete_json(SYSTEM_PROMPT, repair_prompt))
            except ValueError as exc:
                raise JobAnalysisError(
                    "The AI returned data that failed JSON validation."
                ) from exc
    except LLMError as exc:
        raise JobAnalysisError(
            "The AI service is unavailable right now. Please try again."
        ) from exc


def _extract_title(text: str, lines: list[str]) -> str:
    for line in lines[:10]:
        match = _TITLE_LABEL_RE.match(line)
        if match:
            candidate = match.group(1).strip(" -–\t")
            if candidate:
                return candidate[:200]

    for line in lines[:10]:
        if (
            len(line) <= 90
            and _TITLE_WORD_RE.search(line)
            and line.count(",") <= 3
            and not line.endswith(".")
        ):
            return line.strip(" -–:\t")[:200]

    return lines[0][:200] if lines else "Untitled Job"


def _collect(lines: list[str], pattern: re.Pattern[str], limit: int = 10) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        line = _BULLET_RE.sub("", raw).strip()
        if not line or not pattern.search(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(line[:300])
        if len(found) >= limit:
            break
    return found


def analyze_heuristic(text: str) -> JobAnalysisResult:
    """Rule-based extraction used when no LLM key is configured."""
    lines = text.splitlines()

    languages = detect(text, PROGRAMMING_LANGUAGES)
    frameworks = detect(text, FRAMEWORKS)
    databases = detect(text, DATABASES)
    cloud = detect(text, CLOUD_TECHNOLOGIES)
    tools = detect_tools(text)
    soft = detect(text, SOFT_SKILLS)

    required_found: set[str] = set()
    preferred_found: set[str] = set()
    mode = "required"

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()

        if _PREFERRED_HEADING.match(lower):
            mode = "preferred"
        elif _REQUIRED_HEADING.match(lower):
            mode = "required"

        if (
            _PREFERRED_HEADING.search(lower)
            or "a plus" in lower
            or "an advantage" in lower
        ):
            line_mode = "preferred"
        elif _REQUIRED_HEADING.search(lower):
            line_mode = "required"
        else:
            line_mode = mode

        terms = (
            set(detect(line, PROGRAMMING_LANGUAGES))
            | set(detect(line, FRAMEWORKS))
            | set(detect(line, DATABASES))
            | set(detect(line, CLOUD_TECHNOLOGIES))
            | set(detect_tools(line))
        )
        if not terms:
            continue
        target = preferred_found if line_mode == "preferred" else required_found
        target.update(terms)

    preferred_found -= required_found
    ordered = languages + frameworks + databases + cloud + tools
    required_skills = [term for term in ordered if term in required_found]
    preferred_skills = [term for term in ordered if term in preferred_found]

    return JobAnalysisResult(
        job_title=_extract_title(text, [line.strip() for line in lines if line.strip()]),
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        programming_languages=languages,
        frameworks=frameworks,
        databases=databases,
        cloud_technologies=cloud,
        tools=tools,
        soft_skills=soft,
        experience_requirements=_collect(lines, _EXPERIENCE_RE),
        education_requirements=_collect(lines, _EDUCATION_RE),
    )


def analyze_job_description(text: str) -> tuple[JobAnalysisResult, str]:
    """Analyze text, returning ``(result, engine)``."""
    if getattr(settings, "llm_enabled", False):
        return analyze_with_llm(text), "llm"
    return analyze_heuristic(text), "heuristic"
