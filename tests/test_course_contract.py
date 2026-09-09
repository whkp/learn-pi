"""Tests for the pinned source and chapter teaching contracts."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_course_contract


ROOT = Path(__file__).resolve().parents[1]


class CourseContractTests(unittest.TestCase):
    def test_source_map_declares_the_pinned_pi_baseline(self) -> None:
        result = check_course_contract.validate_source_map(ROOT / "docs" / "pi-source-map.md")

        self.assertEqual([], result.errors)

    def test_invalid_source_map_marker_reports_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_map = Path(directory) / "pi-source-map.md"
            source_map.write_text(
                "<!-- pi-baseline: version=0.85.1 commit=not-a-commit -->\n",
                encoding="utf-8",
            )

            result = check_course_contract.validate_source_map(source_map)

        self.assertTrue(result.errors)

    def test_invalid_manifest_entry_reports_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs_dir = Path(directory) / "docs"
            docs_dir.mkdir()
            (docs_dir / "00-course-map.md").write_text(
                "\n".join(
                    (
                        "# Map",
                        "<!-- course-chapter-manifest:start -->",
                        "- not-a-numbered-chapter.md",
                        "<!-- course-chapter-manifest:end -->",
                        "## 学习目标",
                        "## 当前 Pi 行为",
                        "## Python 实验",
                        "## 验证方式",
                        "## 边界与安全",
                    )
                ),
                encoding="utf-8",
            )

            result = check_course_contract.validate_chapters(docs_dir)

        self.assertTrue(result.errors)

    def test_manifest_absent_chapter_discovery_is_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs_dir = Path(directory) / "docs"
            docs_dir.mkdir()
            (docs_dir / "00-course-map.md").write_text("# Map\n", encoding="utf-8")
            for chapter in ("02-second", "01-first"):
                chapter_dir = docs_dir / chapter
                chapter_dir.mkdir()
                (chapter_dir / "README.md").write_text("# Chapter\n", encoding="utf-8")

            reverse_glob_order = [
                docs_dir / "02-second" / "README.md",
                docs_dir / "01-first" / "README.md",
            ]
            with patch.object(check_course_contract.Path, "glob", return_value=reverse_glob_order):
                chapters = check_course_contract.discover_chapters(docs_dir)

        self.assertEqual(
            ["00-course-map.md", "01-first/README.md", "02-second/README.md"],
            [chapter.relative_to(docs_dir).as_posix() for chapter in chapters],
        )

    def test_all_declared_chapters_have_the_teaching_contract(self) -> None:
        result = check_course_contract.validate_chapters(ROOT / "docs")

        self.assertEqual([], result.errors)


if __name__ == "__main__":
    unittest.main()
