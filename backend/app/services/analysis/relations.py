"""Skill canonicalisation and a curated, deterministic partial-credit map.

A skill is PARTIAL when the resume contains a recognised close relative of the
job's skill (e.g. the job asks for SQL and the resume lists PostgreSQL). The
relations are static data, never produced by an LLM.
"""

from app.schemas.analysis import SkillStatus
from app.services.jobs.keywords import CLOUD_TECHNOLOGIES, SOFT_SKILLS
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

_PARTIAL_DEFINITIONS: dict[str, set[str]] = {
    "SQL": {"PostgreSQL", "MySQL", "SQLite", "MariaDB", "Oracle", "SQL Server", "DBMS"},
    "PostgreSQL": {"SQL", "MySQL", "MariaDB"},
    "MySQL": {"SQL", "PostgreSQL", "MariaDB"},
    "MongoDB": {"SQL", "DynamoDB", "Firebase", "Cassandra"},
    "JavaScript": {"TypeScript", "Node.js", "React", "Angular", "Vue"},
    "TypeScript": {"JavaScript", "Node.js", "React", "Angular", "Vue"},
    "Java": {"Kotlin", "Scala", "Spring"},
    "Kotlin": {"Java", "Scala"},
    "C#": {".NET", "Java"},
    ".NET": {"C#", "ASP.NET"},
    "Go": {"Rust", "C++"},
    "Rust": {"Go", "C++"},
    "C++": {"C", "Go", "Rust"},
    "Python": {"R", "Ruby"},
    "R": {"Python", "MATLAB"},
    "React": {"React Native", "Next.js", "Vue", "Angular"},
    "Next.js": {"React", "Node.js"},
    "React Native": {"React", "Flutter"},
    "Angular": {"React", "Vue", "TypeScript"},
    "Vue": {"React", "Angular", "TypeScript"},
    "Node.js": {"JavaScript", "TypeScript", "Express", "Next.js"},
    "Express": {"Node.js", "FastAPI", "Django", "Flask"},
    "FastAPI": {"Django", "Flask", "Express", "Spring"},
    "Django": {"Flask", "FastAPI", "Spring"},
    "Flask": {"Django", "FastAPI", "Express"},
    "Spring": {"Java", "Django", "FastAPI"},
    "Docker": {"Kubernetes", "CI/CD", "Jenkins"},
    "Kubernetes": {"Docker", "Ansible", "Terraform"},
    "Jenkins": {"CI/CD", "Docker", "GitLab"},
    "Terraform": {"Ansible", "Kubernetes", "Cloud Computing"},
    "AWS": {"Azure", "GCP", "Cloud Computing"},
    "Azure": {"AWS", "GCP", "Cloud Computing"},
    "GCP": {"AWS", "Azure", "Cloud Computing"},
    "Git": {"GitHub", "GitLab"},
    "GitHub": {"Git", "GitLab"},
    "GitLab": {"Git", "GitHub"},
    "REST API": {"GraphQL", "Express", "FastAPI", "Django", "Spring"},
    "GraphQL": {"REST API", "Node.js"},
    "Machine Learning": {
        "Deep Learning",
        "TensorFlow",
        "PyTorch",
        "scikit-learn",
        "Data Analysis",
    },
    "Deep Learning": {"Machine Learning", "TensorFlow", "PyTorch", "Keras"},
    "TensorFlow": {"PyTorch", "Keras", "Machine Learning", "Deep Learning"},
    "PyTorch": {"TensorFlow", "Keras", "Machine Learning", "Deep Learning"},
    "scikit-learn": {"Machine Learning", "Pandas", "NumPy"},
    "Data Analysis": {"Machine Learning", "Pandas", "NumPy", "SQL"},
    "Communication": {"Presentation Skills", "Interpersonal Skills", "Leadership"},
    "Teamwork": {"Collaboration", "Interpersonal Skills", "Leadership"},
    "Collaboration": {"Teamwork", "Communication", "Stakeholder Management"},
    "Leadership": {"Mentoring", "Teamwork", "Stakeholder Management"},
    "Problem Solving": {"Critical Thinking", "Analytical Skills"},
    "Critical Thinking": {"Problem Solving", "Analytical Skills"},
    "Adaptability": {"Ownership", "Time Management"},
    "Time Management": {"Ownership", "Adaptability"},
}


def canonicalize(name: str) -> str:
    """Map a free-form skill name to its canonical catalogue name if possible."""
    cleaned = name.strip()
    key = cleaned.casefold()
    for catalog in _CATALOGS:
        for canonical, aliases in catalog.items():
            candidates = [canonical, *aliases]
            if any(key == candidate.casefold() for candidate in candidates):
                return canonical
    return cleaned


_PARTIAL: dict[str, set[str]] = {
    canonicalize(key): {canonicalize(value) for value in values}
    for key, values in _PARTIAL_DEFINITIONS.items()
}


def related_to(skill: str) -> set[str]:
    """Both declared and reverse relations, excluding the skill itself."""
    canonical = canonicalize(skill)
    related = set(_PARTIAL.get(canonical, set()))
    for source, targets in _PARTIAL.items():
        if canonical in targets:
            related.add(source)
    related.discard(canonical)
    return related


def classify(skill: str, resume_skills: set[str]) -> SkillStatus:
    """Classify one job skill against the (canonicalised) resume skill set."""
    canonical = canonicalize(skill)
    if canonical in resume_skills:
        return SkillStatus.MATCH
    if related_to(canonical) & resume_skills:
        return SkillStatus.PARTIAL
    return SkillStatus.MISSING
