"""Text cleaning: normalise line endings, whitespace and control characters."""

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_BLANK_RUN = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub(" ", text)

    lines: list[str] = []
    for raw_line in text.split("\n"):
        line = _MULTI_SPACE.sub(" ", raw_line).strip()
        if line in {"•", "·", "-", "–", "—", "*"}:
            line = ""
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = _BLANK_RUN.sub("\n\n", cleaned)
    return cleaned.strip()
