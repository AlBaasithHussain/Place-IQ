"""Keyword catalogues + matching helpers for job-description analysis.

Technology catalogues are shared with the resume extractor so a skill detected
in a CV and the same skill required by a job line up by canonical name.
"""

import re

from app.services.resume.extractor import (
    DATABASES,
    FRAMEWORKS,
    PROGRAMMING_LANGUAGES,
    TOOLS,
)

CLOUD_TECHNOLOGIES: dict[str, list[str]] = {
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure": ["azure", "microsoft azure"],
    "GCP": ["gcp", "google cloud", "google cloud platform", "bigquery"],
    "Heroku": ["heroku"],
    "DigitalOcean": ["digitalocean", "digital ocean"],
    "Vercel": ["vercel"],
    "Netlify": ["netlify"],
    "Cloudflare": ["cloudflare"],
    "OpenShift": ["openshift"],
    "IBM Cloud": ["ibm cloud"],
}

SOFT_SKILLS: dict[str, list[str]] = {
    "Communication": ["communication"],
    "Teamwork": ["teamwork", "team work"],
    "Collaboration": ["collaboration", "collaborate"],
    "Leadership": ["leadership"],
    "Problem Solving": ["problem solving", "problem-solving"],
    "Critical Thinking": ["critical thinking"],
    "Analytical Skills": ["analytical skills", "analytical thinking"],
    "Time Management": ["time management"],
    "Adaptability": ["adaptability", "adaptable"],
    "Attention to Detail": ["attention to detail", "detail-oriented", "detail oriented"],
    "Interpersonal Skills": ["interpersonal skills", "interpersonal"],
    "Presentation Skills": ["presentation skills", "presentation"],
    "Creativity": ["creativity", "creative thinking"],
    "Mentoring": ["mentoring", "mentorship"],
    "Ownership": ["ownership"],
    "Stakeholder Management": ["stakeholder management"],
}

_CASE_SENSITIVE_ALIASES = {"C", "R", "Go"}
_LEFT = r"(?<![A-Za-z0-9+#.])"
_RIGHT = r"(?![A-Za-z0-9+#])"


def contains_alias(text: str, alias: str) -> bool:
    pattern = _LEFT + re.escape(alias) + _RIGHT
    if alias in _CASE_SENSITIVE_ALIASES:
        return re.search(pattern, text) is not None
    return re.search(pattern, text, re.IGNORECASE) is not None


def detect(text: str, catalog: dict[str, list[str]]) -> list[str]:
    """Return canonical names from ``catalog`` mentioned in ``text``."""
    found = [
        canonical
        for canonical, aliases in catalog.items()
        if any(contains_alias(text, alias) for alias in aliases)
    ]
    return sorted(found)


def detect_tools(text: str) -> list[str]:
    """Tools, excluding anything that is better classified as cloud tech."""
    return [tool for tool in detect(text, TOOLS) if tool not in CLOUD_TECHNOLOGIES]
