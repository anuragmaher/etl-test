"""Convert a Google Docs API document JSON to Markdown."""

HEADING_MAP = {
    "HEADING_1": "# ",
    "HEADING_2": "## ",
    "HEADING_3": "### ",
    "HEADING_4": "#### ",
    "HEADING_5": "##### ",
    "HEADING_6": "###### ",
}


def _format_text_run(text_run: dict) -> str:
    content = text_run.get("content", "")
    style = text_run.get("textStyle", {})

    # Don't format whitespace-only content
    stripped = content.strip()
    if not stripped:
        return content

    leading = content[: len(content) - len(content.lstrip())]
    trailing = content[len(content.rstrip()) :]
    formatted = stripped

    link = style.get("link", {}).get("url")
    bold = style.get("bold", False)
    italic = style.get("italic", False)

    if bold and italic:
        formatted = f"***{formatted}***"
    elif bold:
        formatted = f"**{formatted}**"
    elif italic:
        formatted = f"*{formatted}*"

    if link:
        formatted = f"[{formatted}]({link})"

    return leading + formatted + trailing


def _convert_paragraph(paragraph: dict, doc: dict) -> str:
    style = paragraph.get("paragraphStyle", {})
    named_style = style.get("namedStyleType", "NORMAL_TEXT")

    # Build the text content from all elements
    text_parts = []
    for element in paragraph.get("elements", []):
        if "textRun" in element:
            text_parts.append(_format_text_run(element["textRun"]))
        elif "inlineObjectElement" in element:
            text_parts.append("[image]")

    text = "".join(text_parts).rstrip("\n")

    # Check if this is a list item
    bullet = paragraph.get("bullet")
    if bullet:
        list_id = bullet.get("listId", "")
        nesting = bullet.get("nestingLevel", 0)
        indent = "  " * nesting

        # Determine ordered vs unordered from list properties
        lists = doc.get("lists", {})
        list_props = lists.get(list_id, {}).get("listProperties", {})
        nesting_levels = list_props.get("nestingLevels", [])

        is_ordered = False
        if nesting < len(nesting_levels):
            glyph_type = nesting_levels[nesting].get("glyphType", "")
            if glyph_type in ("DECIMAL", "ALPHA", "ROMAN", "UPPER_ALPHA", "UPPER_ROMAN"):
                is_ordered = True

        if is_ordered:
            return f"{indent}1. {text}"
        else:
            return f"{indent}- {text}"

    # Headings
    prefix = HEADING_MAP.get(named_style, "")
    if prefix:
        return f"{prefix}{text}"

    return text


def _convert_table(table: dict, doc: dict) -> str:
    rows = table.get("tableRows", [])
    if not rows:
        return ""

    md_rows = []
    for row in rows:
        cells = []
        for cell in row.get("tableCells", []):
            # Each cell contains structural elements (paragraphs)
            cell_text_parts = []
            for element in cell.get("content", []):
                if "paragraph" in element:
                    cell_text_parts.append(
                        _convert_paragraph(element["paragraph"], doc)
                    )
            cells.append(" ".join(cell_text_parts).strip())
        md_rows.append("| " + " | ".join(cells) + " |")

    # Insert header separator after first row
    if len(md_rows) >= 1:
        num_cols = len(rows[0].get("tableCells", []))
        separator = "| " + " | ".join(["---"] * num_cols) + " |"
        md_rows.insert(1, separator)

    return "\n".join(md_rows)


def convert(doc_json: dict) -> str:
    """Convert a Google Docs API document JSON to a Markdown string."""
    body = doc_json.get("body", {})
    content = body.get("content", [])

    parts = []
    prev_had_bullet = False

    for element in content:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            has_bullet = "bullet" in paragraph

            # Add blank line when transitioning out of a list
            if prev_had_bullet and not has_bullet and parts:
                parts.append("")

            md = _convert_paragraph(paragraph, doc_json)
            parts.append(md)
            prev_had_bullet = has_bullet

        elif "table" in element:
            if prev_had_bullet:
                parts.append("")
            parts.append(_convert_table(element["table"], doc_json))
            parts.append("")
            prev_had_bullet = False

        elif "sectionBreak" in element:
            prev_had_bullet = False

    # Join and clean up: collapse 3+ consecutive blank lines to 2
    result = "\n".join(parts)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip() + "\n"
