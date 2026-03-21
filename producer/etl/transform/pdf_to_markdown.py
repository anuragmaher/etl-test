"""Convert a PDF file (as bytes) to Markdown."""

import io

import pdfplumber


def convert(pdf_bytes: bytes) -> str:
    """Convert PDF file bytes to a Markdown string."""
    parts = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text() or ""

            # Extract tables
            tables = page.extract_tables() or []

            if text.strip():
                parts.append(text.strip())

            for table in tables:
                if not table:
                    continue
                md_rows = []
                for j, row in enumerate(table):
                    cells = [(cell or "").strip() for cell in row]
                    md_rows.append("| " + " | ".join(cells) + " |")
                    if j == 0:
                        md_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
                if md_rows:
                    parts.append("\n".join(md_rows))

    result = "\n\n".join(parts)
    return result.strip() + "\n" if result.strip() else "\n"
