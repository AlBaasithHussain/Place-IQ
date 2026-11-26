"""Generate a minimal, valid text PDF for tests (pure Python, no deps)."""


def make_pdf(text: str) -> bytes:
    def esc(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = text.split("\n") or [""]
    parts: list[str] = []
    y = 780
    for line in lines:
        parts.append(f"BT /F1 11 Tf 50 {y} Td ({esc(line)}) Tj ET")
        y -= 16
    stream = "\n".join(parts)

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = "%PDF-1.4\n"
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out.encode("latin-1")))
        out += f"{index} 0 obj\n{obj}\nendobj\n"

    xref_pos = len(out.encode("latin-1"))
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n"
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    )
    return out.encode("latin-1")
