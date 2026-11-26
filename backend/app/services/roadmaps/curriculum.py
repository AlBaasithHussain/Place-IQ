"""Static curricula used by the local roadmap fallback."""

from app.services.analysis.relations import canonicalize

CURRICULA: dict[str, list[str]] = {
    "SQL": [
        "SQL JOIN",
        "GROUP BY",
        "Subqueries",
        "Window Functions",
        "Query optimisation",
    ],
    "PostgreSQL": [
        "SQL JOIN",
        "GROUP BY",
        "Subqueries",
        "Window Functions",
        "Indexes and query plans",
    ],
    "MySQL": [
        "SQL JOIN",
        "GROUP BY",
        "Subqueries",
        "Window Functions",
        "Indexes and query plans",
    ],
    "MongoDB": [
        "Documents and collections",
        "CRUD operations",
        "Aggregation pipeline",
        "Indexing",
        "Data modelling",
    ],
    "Python": [
        "Python syntax and data structures",
        "Functions and modules",
        "Object-oriented Python",
        "Error handling and testing",
        "Performance basics",
    ],
    "JavaScript": [
        "JavaScript fundamentals",
        "DOM and events",
        "Async/await and promises",
        "Modules and tooling",
        "Testing JavaScript",
    ],
    "TypeScript": [
        "TypeScript types",
        "Interfaces and generics",
        "Strict compiler settings",
        "Typing React components",
        "Build and tooling",
    ],
    "React": [
        "Components and props",
        "State and hooks",
        "Forms and validation",
        "Routing",
        "Component testing",
    ],
    "Next.js": [
        "App router basics",
        "Server and client components",
        "Data fetching",
        "Routing and layouts",
        "Deployment",
    ],
    "FastAPI": [
        "FastAPI routing",
        "Request validation with Pydantic",
        "Dependencies and auth",
        "Testing endpoints",
        "Performance and docs",
    ],
    "Django": [
        "Django project structure",
        "Models and migrations",
        "Views and templates",
        "Forms and auth",
        "Testing",
    ],
    "Docker": [
        "Docker concepts",
        "Writing a Dockerfile",
        "Docker Compose",
        "Volumes and networking",
        "Debugging containers",
    ],
    "AWS": [
        "Cloud fundamentals",
        "Compute and storage",
        "IAM and security",
        "Networking basics",
        "Cost and deployment",
    ],
    "Azure": [
        "Azure fundamentals",
        "Compute and storage",
        "Identity and access",
        "Networking basics",
        "Deployment",
    ],
    "Git": [
        "Git basics",
        "Branching and merging",
        "Rebasing and conflict resolution",
        "Pull requests",
        "Team workflows",
    ],
    "Power BI": [
        "Power BI basics",
        "Data modelling",
        "DAX essentials",
        "Dashboards",
        "Performance tuning",
    ],
    "Machine Learning": [
        "ML fundamentals",
        "Data preparation",
        "Supervised learning",
        "Model evaluation",
        "Deployment basics",
    ],
    "Data Analysis": [
        "Data cleaning",
        "Exploratory analysis",
        "SQL for analysts",
        "Visualisation",
        "Storytelling with data",
    ],
    "Communication": [
        "Structured communication",
        "Presentation skills",
        "Stakeholder updates",
        "Interview answers",
        "Written communication",
    ],
    "Teamwork": [
        "Collaboration basics",
        "Code reviews",
        "Pair programming",
        "Feedback",
        "Team rituals",
    ],
}

DEFAULT_TOPICS = [
    "Core concepts",
    "Guided examples",
    "Hands-on exercises",
    "Review and refactor",
    "Interview practice",
]

DEFAULT_PRACTICE = [
    "Complete three short exercises",
    "Explain the concept aloud",
    "Solve one timed problem",
    "Review sample solutions",
    "Write a short summary of what you learned",
]


def topics_for(skill: str, round_index: int = 0) -> list[str]:
    canonical = canonicalize(skill)
    topics = CURRICULA.get(canonical, DEFAULT_TOPICS)
    offset = round_index % len(topics)
    return topics[offset:] + topics[:offset]


def practice_for(skill: str, day: int) -> list[str]:
    canonical = canonicalize(skill)
    suffix = f"using {canonical}" if canonical in CURRICULA else "on the day's topic"
    return [
        f"Complete three short exercises {suffix}",
        f"Solve one timed problem for Day {day}",
        "Explain your solution in two minutes",
    ]


def mini_project_for(skill: str, day: int, duration: int) -> str:
    canonical = canonicalize(skill)
    if day == duration:
        return "Build a small end-to-end project and rehearse the interview explanation"
    return f"Build a mini project applying one {canonical} concept from Day {day}"
