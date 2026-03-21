import json
import os

from etl.transform.gdocs_to_markdown import convert

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


def test_full_document_conversion():
    doc = _load_fixture("sample_doc.json")
    md = convert(doc)

    assert "# Main Heading" in md
    assert "## Sub Heading" in md
    assert "**bold text**" in md
    assert "*italic text*" in md
    assert "[link](https://example.com)" in md
    assert "- First item" in md
    assert "- Second item" in md
    assert "  - Nested item" in md
    assert "1. Ordered one" in md
    assert "1. Ordered two" in md
    assert "| Name | Value |" in md
    assert "| --- | --- |" in md
    assert "| Alpha | 100 |" in md
    assert "End of document." in md


def test_empty_document():
    doc = {"body": {"content": []}}
    md = convert(doc)
    assert md.strip() == ""


def test_bold_italic_combined():
    doc = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "elements": [
                            {
                                "textRun": {
                                    "content": "both",
                                    "textStyle": {"bold": True, "italic": True},
                                }
                            }
                        ],
                    }
                }
            ]
        }
    }
    md = convert(doc)
    assert "***both***" in md


def test_list_to_paragraph_transition():
    doc = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "bullet": {"listId": "l1", "nestingLevel": 0},
                        "elements": [
                            {"textRun": {"content": "item\n", "textStyle": {}}}
                        ],
                    }
                },
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        "elements": [
                            {"textRun": {"content": "paragraph\n", "textStyle": {}}}
                        ],
                    }
                },
            ]
        },
        "lists": {
            "l1": {
                "listProperties": {
                    "nestingLevels": [{"glyphType": "GLYPH_TYPE_UNSPECIFIED"}]
                }
            }
        },
    }
    md = convert(doc)
    # Should have a blank line between list and paragraph
    assert "- item\n\nparagraph" in md
