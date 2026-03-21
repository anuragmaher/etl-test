"""Convert a PDF file (as bytes) to Markdown."""

import io

import pdfplumber


def _table_to_markdown(table: list) -> str:
    """Convert a pdfplumber table to markdown pipe format."""
    if not table:
        return ""

    md_rows = []
    for j, row in enumerate(table):
        # Clean cells: replace newlines with spaces, strip whitespace
        cells = [(cell or "").replace("\n", " ").strip() for cell in row]
        md_rows.append("| " + " | ".join(cells) + " |")
        if j == 0:
            md_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")

    return "\n".join(md_rows)


def _get_text_outside_tables(page) -> str:
    """Extract text from a page excluding areas covered by tables."""
    tables = page.find_tables()
    if not tables:
        return page.extract_text() or ""

    # Get table bounding boxes
    table_bboxes = [t.bbox for t in tables]

    # Crop page to exclude table areas and extract remaining text
    # Work with the full page, filter out chars inside table bboxes
    chars = page.chars
    filtered_chars = []
    for char in chars:
        in_table = False
        for bbox in table_bboxes:
            # bbox is (x0, top, x1, bottom)
            if (bbox[0] <= char["x0"] <= bbox[2] and
                bbox[1] <= char["top"] <= bbox[3]):
                in_table = True
                break
        if not in_table:
            filtered_chars.append(char)

    if not filtered_chars:
        return ""

    # Rebuild text from filtered chars using pdfplumber's crop
    # Simpler approach: crop above/below/between tables
    text_parts = []
    page_top = 0
    page_bottom = page.height

    # Sort table bboxes by vertical position
    sorted_bboxes = sorted(table_bboxes, key=lambda b: b[1])

    # Extract text between tables
    current_top = page_top
    for bbox in sorted_bboxes:
        table_top = bbox[1]
        if table_top > current_top + 5:  # 5pt threshold
            crop = page.within_bbox((0, current_top, page.width, table_top))
            text = crop.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())
        current_top = bbox[3]  # bottom of this table

    # Text after last table
    if current_top < page_bottom - 5:
        try:
            crop = page.within_bbox((0, current_top, page.width, page_bottom))
            text = crop.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())
        except Exception:
            pass

    return "\n\n".join(text_parts)


def convert(pdf_bytes: bytes) -> str:
    """Convert PDF file bytes to a Markdown string."""
    parts = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()

            if tables:
                # Page has tables: extract text outside tables + tables separately
                non_table_text = _get_text_outside_tables(page)
                if non_table_text:
                    parts.append(non_table_text)

                for table in tables:
                    table_data = table.extract()
                    md = _table_to_markdown(table_data)
                    if md:
                        parts.append(md)
            else:
                # No tables: just extract text
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text.strip())

    result = "\n\n".join(parts)
    return result.strip() + "\n" if result.strip() else "\n"
