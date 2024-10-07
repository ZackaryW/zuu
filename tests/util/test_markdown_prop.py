import pytest
from zuu.string import extract_md_meta, get_md_meta, append_meta, update_meta, dump_meta

class TestMarkdownMeta:
    @pytest.fixture
    def sample_md_content(self):
        return """
---
title: Sample Document
author: John Doe
---

# Sample Markdown
This is a sample markdown file.
"""

    @pytest.fixture
    def sample_md_file(self, tmp_path, sample_md_content):
        md_file = tmp_path / "sample.md"
        md_file.write_text(sample_md_content)
        return md_file

    def test_extract_md_meta(self, sample_md_content):
        meta = extract_md_meta(sample_md_content)
        assert meta == {"title": "Sample Document", "author": "John Doe"}

    def test_extract_md_meta_no_meta(self):
        md_content = "# Sample Markdown\nThis is a sample markdown file."
        meta = extract_md_meta(md_content)
        assert meta == {}

    def test_get_md_meta(self, sample_md_file):
        meta = get_md_meta(sample_md_file)
        assert meta == {"title": "Sample Document", "author": "John Doe"}

    def test_append_meta(self, sample_md_content):
        new_meta = {"date": "2023-10-01"}
        updated_content = append_meta(sample_md_content, new_meta)
        assert "---\ntitle: Sample Document\nauthor: John Doe\ndate: '2023-10-01'\n---\n" in updated_content

    def test_append_meta_no_existing_meta(self):
        md_content = "# Sample Markdown\nThis is a sample markdown file."
        new_meta = {"title": "New Title"}
        updated_content = append_meta(md_content, new_meta)
        assert updated_content.startswith("---\ntitle: New Title\n---\n# Sample Markdown")

    def test_update_meta(self, sample_md_file):
        new_meta = {"date": "2023-10-01"}
        updated_content = update_meta(sample_md_file, new_meta)
        assert "---\ntitle: Sample Document\nauthor: John Doe\ndate: '2023-10-01'\n---" in updated_content

    def test_dump_meta(self, sample_md_file):
        new_meta = {"date": "2023-10-01"}
        dump_meta(sample_md_file, new_meta)
        with open(sample_md_file, "r") as f:
            content = f.read()
        assert "date: '2023-10-01'\n---" in content
