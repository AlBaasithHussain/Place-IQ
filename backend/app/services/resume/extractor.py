"""Heuristic resume information extraction.

Perfect resume parsing needs an LLM or a paid service. This module uses
transparent, dependency-free heuristics: a curated keyword catalogue for
technologies plus section/bullet detection for education, projects,
certifications and experience. It works well for typical text-based resumes
and degrades gracefully (returns empty lists) when it is unsure.
"""

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# ---------------------------------------------------------------------------
# Technology catalogues: canonical display name -> aliases
# ---------------------------------------------------------------------------
PROGRAMMING_LANGUAGES: dict[str, list[str]] = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript", "ts"],
    "C++": ["c++"],
    "C#": ["c#"],
    "C": ["C"],
    "Objective-C": ["objective-c", "objective c"],
    "Go": ["Go", "Golang"],
    "Rust": ["rust"],
    "Ruby": ["ruby"],
    "PHP": ["php"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "Scala": ["scala"],
    "R": ["R"],
    "MATLAB": ["matlab"],
    "Dart": ["dart"],
    "Perl": ["perl"],
    "SQL": ["sql"],
}

FRAMEWORKS: dict[str, list[str]] = {
    "React": ["react", "react.js", "reactjs"],
    "Angular": ["angular"],
    "Vue": ["vue", "vue.js", "vuejs"],
    "Next.js": ["next.js", "nextjs"],
    "Node.js": ["node.js", "nodejs"],
    "Express": ["express", "express.js", "expressjs"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Spring": ["spring", "spring boot", "springboot"],
    ".NET": ["asp.net", ".net", "dotnet"],
    "Flutter": ["flutter"],
    "React Native": ["react native"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Keras": ["keras"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Tailwind CSS": ["tailwind", "tailwind css", "tailwindcss"],
    "Bootstrap": ["bootstrap"],
    "Ruby on Rails": ["ruby on rails", "rails"],
    "Laravel": ["laravel"],
    "jQuery": ["jquery"],
    "GraphQL": ["graphql"],
    "Redux": ["redux"],
}

DATABASES: dict[str, list[str]] = {
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "SQLite": ["sqlite"],
    "Redis": ["redis"],
    "Oracle": ["oracle"],
    "SQL Server": ["sql server", "mssql"],
    "Cassandra": ["cassandra"],
    "DynamoDB": ["dynamodb"],
    "Firebase": ["firebase", "firestore"],
    "Elasticsearch": ["elasticsearch"],
    "Snowflake": ["snowflake"],
    "MariaDB": ["mariadb"],
    "Neo4j": ["neo4j"],
    "Supabase": ["supabase"],
}

TOOLS: dict[str, list[str]] = {
    "Git": ["git"],
    "GitHub": ["github"],
    "GitLab": ["gitlab"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Jenkins": ["jenkins"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Linux": ["linux"],
    "Jira": ["jira"],
    "Figma": ["figma"],
    "Postman": ["postman"],
    "VS Code": ["vs code", "visual studio code", "vscode"],
    "Eclipse": ["eclipse"],
    "Terraform": ["terraform"],
    "Ansible": ["ansible"],
    "Nginx": ["nginx"],
    "Maven": ["maven"],
    "Gradle": ["gradle"],
    "Webpack": ["webpack"],
    "Vite": ["vite"],
    "CI/CD": ["ci/cd", "cicd"],
    "Kafka": ["kafka", "apache kafka"],
    "RabbitMQ": ["rabbitmq"],
    "Spark": ["apache spark", "pyspark"],
    "Hadoop": ["hadoop"],
    "Selenium": ["selenium"],
    "Jest": ["jest"],
    "Pytest": ["pytest"],
}

GENERAL_SKILLS: dict[str, list[str]] = {
    "Machine Learning": ["machine learning"],
    "Deep Learning": ["deep learning"],
    "Data Structures": ["data structures"],
    "Algorithms": ["algorithms"],
    "Operating Systems": ["operating systems", "operating system"],
    "Computer Networks": ["computer networks", "networking"],
    "DBMS": ["dbms", "database management"],
    "OOP": ["object-oriented programming", "object oriented programming", "oop"],
    "REST API": ["rest api", "rest apis", "restful"],
    "Microservices": ["microservices", "microservice"],
    "Agile": ["agile"],
    "Scrum": ["scrum"],
    "Leadership": ["leadership"],
    "Teamwork": ["teamwork", "team work"],
    "Communication": ["communication"],
    "Problem Solving": ["problem solving", "problem-solving"],
    "Critical Thinking": ["critical thinking"],
    "Time Management": ["time management"],
    "Data Analysis": ["data analysis", "data analytics"],
    "Web Development": ["web development", "full stack", "full-stack"],
    "Mobile Development": ["mobile development", "android", "ios"],
    "Cloud Computing": ["cloud computing"],
    "DevOps": ["devops", "dev ops"],
    "System Design": ["system design"],
    "Unit Testing": ["unit testing", "unit tests"],
    "Project Management": ["project management"],
}

# Aliases that must match case-sensitively (single letters / ambiguous words).
_CASE_SENSITIVE_ALIASES = {"C", "R", "Go"}

_LEFT = r"(?<![A-Za-z0-9+#.])"
_RIGHT = r"(?![A-Za-z0-9+#])"


def _contains_alias(text: str, alias: str) -> bool:
    pattern = _LEFT + re.escape(alias) + _RIGHT
    if alias in _CASE_SENSITIVE_ALIASES:
        return re.search(pattern, text) is not None
    return re.search(pattern, text, re.IGNORECASE) is not None


def _detect(text: str, catalog: dict[str, list[str]]) -> list[str]:
    found = [
        canonical
        for canonical, aliases in catalog.items()
        if any(_contains_alias(text, alias) for alias in aliases)
    ]
    return sorted(found)


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------
SECTION_ALIASES: dict[str, list[str]] = {
    "education": [
        "education",
        "academic background",
        "academics",
        "qualifications",
        "educational qualifications",
        "academic qualifications",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "employment",
        "work history",
        "internships",
        "internship experience",
    ],
    "projects": [
        "projects",
        "academic projects",
        "personal projects",
        "project experience",
        "key projects",
    ],
    "certifications": [
        "certifications",
        "certification",
        "licenses and certifications",
        "licenses & certifications",
        "courses",
        "certificates",
    ],
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "objective",
        "career objective",
        "about me",
    ],
    "achievements": ["achievements", "awards", "honors", "honours", "accomplishments"],
    "languages_spoken": ["languages", "languages known"],
    "interests": ["interests", "hobbies", "activities"],
    "references": ["references"],
    "publications": ["publications", "research", "papers"],
    "volunteer": ["volunteer", "volunteering", "community service"],
}

_ALIAS_TO_SECTION = {
    alias: section for section, aliases in SECTION_ALIASES.items() for alias in aliases
}

_BULLET_RE = re.compile(r"^[\s\-–—•*·o]\s*")
_DEGREE_RE = re.compile(
    r"\b(bachelor(?:'s)?|master(?:'s)?|b\.?tech|m\.?tech|b\.?sc|m\.?sc|bca|mca|mba|ph\.?d|b\.?com|diploma|b\.e\.)\b",
    re.IGNORECASE,
)


def _normalise_heading(line: str) -> str:
    text = line.strip().lower().strip(" :—-–")
    text = re.sub(r"[^a-z& ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _detect_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 45:
        return None
    return _ALIAS_TO_SECTION.get(_normalise_heading(stripped))


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        heading = _detect_heading(line)
        if heading is not None:
            current = heading
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return sections


def _section_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        cleaned = _BULLET_RE.sub("", line).strip()
        if not cleaned or not re.search(r"[A-Za-z0-9]", cleaned):
            continue
        items.append(cleaned)
    return items[:30]


# ---------------------------------------------------------------------------
# Name
# ---------------------------------------------------------------------------
_NAME_SKIP = {
    "resume",
    "curriculum vitae",
    "cv",
    "profile",
    "summary",
    "contact",
    "objective",
}


def _extract_name(lines: list[str], email: str | None) -> str | None:
    for line in lines[:12]:
        candidate = line.strip()
        if not candidate or len(candidate) > 60:
            continue
        lowered = candidate.lower()
        if any(lowered == skip or lowered.startswith(skip + ":") for skip in _NAME_SKIP):
            continue
        if email and email in candidate:
            continue
        if "@" in candidate or "http" in lowered or re.search(r"\d", candidate):
            continue
        words = candidate.split()
        if 2 <= len(words) <= 4 and all(
            re.fullmatch(r"[A-Z][A-Za-z.'\-]*", word) for word in words
        ):
            return candidate

    for line in lines[:6]:
        candidate = line.strip()
        if (
            1 <= len(candidate.split()) <= 4
            and re.fullmatch(r"[A-Za-z][A-Za-z.'\- ]+", candidate)
            and candidate.lower() not in _NAME_SKIP
        ):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_resume_data(text: str) -> dict:
    """Return a structured dict matching ``ParsedResume``."""
    lines = text.split("\n")

    email_match = EMAIL_RE.search(text)
    email = email_match.group(0) if email_match else None
    name = _extract_name(lines, email)

    sections = _split_sections(lines)

    education = _section_items(sections.get("education", []))
    if not education:
        education = [line.strip() for line in lines if _DEGREE_RE.search(line)][:10]

    languages = _detect(text, PROGRAMMING_LANGUAGES)
    frameworks = _detect(text, FRAMEWORKS)
    databases = _detect(text, DATABASES)
    tools = _detect(text, TOOLS)
    general = _detect(text, GENERAL_SKILLS)

    skills = sorted(
        set(languages) | set(frameworks) | set(databases) | set(tools) | set(general)
    )

    return {
        "name": name,
        "email": email,
        "education": education,
        "skills": skills,
        "programming_languages": languages,
        "frameworks": frameworks,
        "databases": databases,
        "tools": tools,
        "projects": _section_items(sections.get("projects", [])),
        "certifications": _section_items(sections.get("certifications", [])),
        "experience": _section_items(sections.get("experience", [])),
    }
