"""Collect canonical skill names from a parsed resume."""

from app.services.jobs.keywords import CLOUD_TECHNOLOGIES, SOFT_SKILLS, detect
from app.services.resume.extractor import (
    DATABASES,
    FRAMEWORKS,
    GENERAL_SKILLS,
    PROGRAMMING_LANGUAGES,
    TOOLS,
)

_CATALOGS = (
    PROGRAMMING_LANGUAGES,
    FRAMEWORKS,
    DATABASES,
    TOOLS,
    GENERAL_SKILLS,
    CLOUD_TECHNOLOGIES,
    SOFT_SKILLS,
)
_PARSED_KEYS = (
    "skills",
    "programming_languages",
    "frameworks",
    "databases",
    "tools",
)


def collect_resume_skills(resume: object) -> list[str]:
    parsed = getattr(resume, "parsed_data", None) or {}
    skills: set[str] = set()
    for key in _PARSED_KEYS:
        skills.update(parsed.get(key, []) or [])
    text = getattr(resume, "raw_text", None) or ""
    for catalog in _CATALOGS:
        skills.update(detect(text, catalog))
    return sorted(skills)
