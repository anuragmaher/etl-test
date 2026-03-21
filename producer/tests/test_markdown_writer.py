import os
import tempfile

from etl.output.markdown_writer import sanitize_filename, write


def test_sanitize_filename_basic():
    assert sanitize_filename("My Document") == "My_Document.md"


def test_sanitize_filename_special_chars():
    assert sanitize_filename("file/with:special*chars?") == "filewithspecialchars.md"


def test_sanitize_filename_empty():
    assert sanitize_filename("") == "untitled.md"


def test_sanitize_filename_long():
    title = "a" * 300
    result = sanitize_filename(title)
    assert result.endswith(".md")
    assert len(result) <= 204  # 200 + ".md"


def test_write_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = write(
            output_dir=tmpdir,
            title="Test Doc",
            source_type="google_docs",
            doc_id="abc123",
            url="https://docs.google.com/document/d/abc123/edit",
            last_modified="2026-01-01T00:00:00Z",
            markdown_content="# Hello\n\nWorld\n",
        )

        assert os.path.exists(filepath)
        with open(filepath) as f:
            content = f.read()

        assert content.startswith("---\n")
        assert 'title: "Test Doc"' in content
        assert "source: google_docs" in content
        assert 'doc_id: "abc123"' in content
        assert "# Hello" in content
        assert "World" in content
