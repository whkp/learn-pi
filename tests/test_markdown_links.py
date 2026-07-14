"""Tests for repository-local Markdown links."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts import check_markdown_links


ROOT = Path(__file__).resolve().parents[1]


class MarkdownLinkTests(unittest.TestCase):
    def test_missing_relative_link_is_reported_from_a_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            (fixture_root / "README.md").write_text(
                "[Missing lesson](missing-lesson.md)\n",
                encoding="utf-8",
            )

            errors = check_markdown_links.find_broken_links(fixture_root)

        self.assertEqual(["README.md: missing-lesson.md"], errors)

    def test_missing_anchor_in_an_existing_local_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            (fixture_root / "chapter.md").write_text("# Existing heading\n", encoding="utf-8")
            (fixture_root / "README.md").write_text(
                "[Missing anchor](chapter.md#missing-heading)\n",
                encoding="utf-8",
            )

            errors = check_markdown_links.find_broken_links(fixture_root)

        self.assertEqual(["README.md: chapter.md#missing-heading"], errors)

    def test_heading_anchors_use_documented_github_style_slugs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            (fixture_root / "chapter.md").write_text(
                "# A Heading!\n## A Heading!\n",
                encoding="utf-8",
            )
            (fixture_root / "README.md").write_text(
                "# Current Page\n"
                "[First heading](chapter.md#a-heading)\n"
                "[Repeated heading](chapter.md#a-heading-1)\n"
                "[Current heading](#current-page)\n",
                encoding="utf-8",
            )

            errors = check_markdown_links.find_broken_links(fixture_root)

        self.assertEqual([], errors)

    def test_balanced_parentheses_in_a_path_keep_an_outside_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            (fixture_root / "chapter (draft).md").write_text(
                "# Present anchor\n",
                encoding="utf-8",
            )
            (fixture_root / "README.md").write_text(
                "[Valid](chapter (draft).md#present-anchor)\n"
                "[Missing anchor](chapter (draft).md#missing-anchor)\n"
                "[Missing file](missing (draft).md)\n",
                encoding="utf-8",
            )

            errors = check_markdown_links.find_broken_links(fixture_root)

        self.assertEqual(
            [
                "README.md: chapter (draft).md#missing-anchor",
                "README.md: missing (draft).md",
            ],
            errors,
        )

    def test_existing_outside_repository_target_is_reported_without_reading_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_parent = Path(directory)
            fixture_root = fixture_parent / "repository"
            fixture_root.mkdir()
            (fixture_parent / "outside.md").write_text("# Outside\n", encoding="utf-8")
            (fixture_root / "README.md").write_text(
                "[Outside](../outside.md#outside)\n",
                encoding="utf-8",
            )

            errors = check_markdown_links.find_broken_links(fixture_root)

        self.assertEqual(["README.md: ../outside.md#outside"], errors)

    def test_repository_markdown_links_resolve(self) -> None:
        self.assertEqual([], check_markdown_links.find_broken_links(ROOT))


if __name__ == "__main__":
    unittest.main()
