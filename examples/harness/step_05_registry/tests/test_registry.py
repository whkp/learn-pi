"""B05 测试：工具注册表。"""

from __future__ import annotations

import unittest

from step_05_registry.registry import (
    ToolRegistry,
    make_list_files_tool,
    make_read_file_tool,
)


class ToolRegistryTests(unittest.TestCase):
    def test_add_and_get(self) -> None:
        registry = ToolRegistry()
        registry.add(make_read_file_tool())
        tool = registry.get("read_file")
        self.assertIsNotNone(tool)
        self.assertEqual("read_file", tool.name)  # type: ignore[union-attr]

    def test_add_duplicate_rejected(self) -> None:
        registry = ToolRegistry()
        registry.add(make_read_file_tool())
        with self.assertRaises(ValueError):
            registry.add(make_read_file_tool())

    def test_unknown_tool_returns_none(self) -> None:
        registry = ToolRegistry()
        self.assertIsNone(registry.get("missing"))

    def test_names_sorted(self) -> None:
        registry = ToolRegistry()
        registry.add(make_list_files_tool())
        registry.add(make_read_file_tool())
        self.assertEqual(("list_files", "read_file"), registry.names())


if __name__ == "__main__":
    unittest.main()
