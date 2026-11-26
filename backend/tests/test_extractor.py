"""Unit tests for text cleaning and heuristic information extraction."""

from app.services.resume.cleaner import clean_text
from app.services.resume.extractor import extract_resume_data

SAMPLE = """Jane Smith
jane.smith@example.com

Education
B.Tech in Computer Science, IIT Delhi, 2026

Skills
Python, Java, React, Node.js, PostgreSQL, MongoDB, Docker, Git, Machine Learning

Projects
Resume Analyzer - built with FastAPI.
Chat App - React and Node.js.

Certifications
AWS Certified Cloud Practitioner

Experience
Software Engineer Intern at Acme Corp
"""


def _extract():
    return extract_resume_data(clean_text(SAMPLE))


def test_extracts_name_and_email():
    data = _extract()
    assert data["name"] == "Jane Smith"
    assert data["email"] == "jane.smith@example.com"


def test_extracts_programming_languages():
    languages = _extract()["programming_languages"]
    assert "Python" in languages
    assert "Java" in languages
    # "java" must not be matched inside "javascript"
    assert not any(lang.lower() == "javascript" for lang in languages)


def test_extracts_frameworks_databases_tools():
    data = _extract()
    assert "React" in data["frameworks"]
    assert "Node.js" in data["frameworks"]
    assert {"PostgreSQL", "MongoDB"} <= set(data["databases"])
    assert {"Docker", "Git"} <= set(data["tools"])


def test_extracts_general_skills_and_union():
    data = _extract()
    assert "Machine Learning" in data["skills"]
    # skills is the union of all categories
    assert "Python" in data["skills"]
    assert "React" in data["skills"]
    assert "PostgreSQL" in data["skills"]


def test_extracts_sections():
    data = _extract()
    assert any("B.Tech" in item for item in data["education"])
    assert any("Resume Analyzer" in item for item in data["projects"])
    assert any("AWS" in item for item in data["certifications"])
    assert any("Software Engineer" in item for item in data["experience"])


def test_clean_text_normalises_whitespace():
    assert clean_text("  Hello\t\tWorld \r\n\r\n\r\nBye  ") == "Hello World\n\nBye"


def test_empty_text_is_graceful():
    data = extract_resume_data(clean_text(""))
    assert data["name"] is None
    assert data["email"] is None
    assert data["skills"] == []
    assert data["education"] == []
