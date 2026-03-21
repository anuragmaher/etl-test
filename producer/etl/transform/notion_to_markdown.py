"""Convert Notion page blocks or database rows to Markdown."""


def _rich_text_to_md(rich_texts: list) -> str:
    """Convert Notion rich_text array to markdown string."""
    parts = []
    for rt in rich_texts:
        text = rt.get("plain_text", "")
        if not text:
            continue

        annotations = rt.get("annotations", {})
        href = rt.get("href")

        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold") and annotations.get("italic"):
            text = f"***{text}***"
        elif annotations.get("bold"):
            text = f"**{text}**"
        elif annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"
        if href:
            text = f"[{text}]({href})"

        parts.append(text)

    return "".join(parts)


def _convert_block(block: dict, depth: int = 0) -> list:
    """Convert a single Notion block to markdown lines."""
    btype = block.get("type", "")
    indent = "  " * depth
    lines = []

    if btype == "paragraph":
        text = _rich_text_to_md(block.get("paragraph", {}).get("rich_text", []))
        lines.append(f"{indent}{text}")

    elif btype in ("heading_1", "heading_2", "heading_3"):
        level = int(btype[-1])
        text = _rich_text_to_md(block.get(btype, {}).get("rich_text", []))
        lines.append(f"{'#' * level} {text}")

    elif btype == "bulleted_list_item":
        text = _rich_text_to_md(block.get("bulleted_list_item", {}).get("rich_text", []))
        lines.append(f"{indent}- {text}")

    elif btype == "numbered_list_item":
        text = _rich_text_to_md(block.get("numbered_list_item", {}).get("rich_text", []))
        lines.append(f"{indent}1. {text}")

    elif btype == "to_do":
        data = block.get("to_do", {})
        text = _rich_text_to_md(data.get("rich_text", []))
        checked = "x" if data.get("checked") else " "
        lines.append(f"{indent}- [{checked}] {text}")

    elif btype == "toggle":
        text = _rich_text_to_md(block.get("toggle", {}).get("rich_text", []))
        lines.append(f"{indent}<details><summary>{text}</summary>")

    elif btype == "code":
        data = block.get("code", {})
        text = _rich_text_to_md(data.get("rich_text", []))
        lang = data.get("language", "")
        lines.append(f"```{lang}")
        lines.append(text)
        lines.append("```")

    elif btype == "quote":
        text = _rich_text_to_md(block.get("quote", {}).get("rich_text", []))
        for line in text.split("\n"):
            lines.append(f"> {line}")

    elif btype == "callout":
        data = block.get("callout", {})
        text = _rich_text_to_md(data.get("rich_text", []))
        icon = ""
        icon_data = data.get("icon")
        if icon_data and icon_data.get("type") == "emoji":
            icon = icon_data.get("emoji", "") + " "
        lines.append(f"> {icon}{text}")

    elif btype == "divider":
        lines.append("---")

    elif btype == "table":
        table_data = block.get("table", {})
        children = block.get("children", [])
        for i, row_block in enumerate(children):
            if row_block.get("type") == "table_row":
                cells = row_block.get("table_row", {}).get("cells", [])
                cell_texts = [_rich_text_to_md(cell) for cell in cells]
                lines.append("| " + " | ".join(cell_texts) + " |")
                if i == 0:
                    lines.append("| " + " | ".join(["---"] * len(cell_texts)) + " |")

    elif btype == "image":
        data = block.get("image", {})
        url = ""
        if data.get("type") == "external":
            url = data.get("external", {}).get("url", "")
        elif data.get("type") == "file":
            url = data.get("file", {}).get("url", "")
        caption = _rich_text_to_md(data.get("caption", []))
        lines.append(f"![{caption}]({url})")

    elif btype == "bookmark":
        url = block.get("bookmark", {}).get("url", "")
        lines.append(f"[{url}]({url})")

    elif btype == "equation":
        expr = block.get("equation", {}).get("expression", "")
        lines.append(f"$${expr}$$")

    elif btype == "child_page":
        title = block.get("child_page", {}).get("title", "")
        lines.append(f"**{title}**")

    elif btype == "child_database":
        title = block.get("child_database", {}).get("title", "")
        lines.append(f"**{title}**")

    # Process children (for toggle, lists with nested content, etc.)
    children = block.get("children", [])
    if children and btype != "table":
        child_depth = depth + 1 if btype in ("bulleted_list_item", "numbered_list_item", "toggle") else depth
        for child in children:
            lines.extend(_convert_block(child, child_depth))

    if btype == "toggle":
        lines.append(f"{indent}</details>")

    return lines


def convert_page(raw_content: dict) -> str:
    """Convert Notion page blocks to Markdown."""
    blocks = raw_content.get("blocks", [])
    lines = []

    for block in blocks:
        block_lines = _convert_block(block)
        lines.extend(block_lines)
        # Add blank line after non-list blocks
        btype = block.get("type", "")
        if btype not in ("bulleted_list_item", "numbered_list_item"):
            lines.append("")

    result = "\n".join(lines)
    # Clean up excessive blank lines
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip() + "\n"


def convert_database(raw_content: dict) -> str:
    """Convert Notion database rows to a Markdown table."""
    rows = raw_content.get("rows", [])
    properties = raw_content.get("properties", {})

    if not rows:
        return "*(Empty database)*\n"

    # Get column order from properties
    columns = sorted(properties.keys(), key=lambda k: properties[k].get("name", k))

    # Build markdown table
    md_lines = []
    md_lines.append("| " + " | ".join(columns) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(columns)) + " |")

    for row in rows:
        cells = [str(row.get(col, "")).replace("\n", " ") for col in columns]
        md_lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(md_lines) + "\n"


def convert(raw_content: dict) -> str:
    """Convert Notion content (page or database) to Markdown."""
    content_type = raw_content.get("type", "page")
    if content_type == "database":
        return convert_database(raw_content)
    return convert_page(raw_content)
