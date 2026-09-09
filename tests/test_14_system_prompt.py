"""Behavior tests for the system-prompt assembly teaching model."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from learn_pi_lab.labs.system_prompt import (
    CONFIG_DIR_NAME,
    ContextFile,
    Skill,
    SystemPromptOptions,
    build_system_prompt,
    demo,
    discover_system_prompt_file,
    resolve_append,
    resolve_persona,
)


def _base_options(**overrides: object) -> SystemPromptOptions:
    options = {
        "cwd": "/work/learn-pi",
        "tool_snippets": {"read": "Read a file", "bash": "Run a command"},
    }
    options.update(overrides)
    return SystemPromptOptions(**options)  # type: ignore[arg-type]


class SystemPromptAssemblyTests(unittest.TestCase):
    def test_default_prompt_contains_persona_tools_and_guidelines(self) -> None:
        prompt = build_system_prompt(_base_options())

        self.assertIn("expert coding assistant", prompt)
        self.assertIn("Available tools:", prompt)
        self.assertIn("Guidelines:", prompt)

    def test_custom_prompt_skips_tools_and_guidelines_segments(self) -> None:
        prompt = build_system_prompt(
            _base_options(custom_prompt="You are a data analysis assistant.")
        )

        self.assertIn("You are a data analysis assistant.", prompt)
        self.assertNotIn("Available tools:", prompt)
        self.assertNotIn("Guidelines:", prompt)

    def test_working_directory_is_appended_on_both_paths(self) -> None:
        for options in (
            _base_options(),
            _base_options(custom_prompt="Custom persona."),
        ):
            with self.subTest(custom=options.custom_prompt is not None):
                self.assertTrue(
                    build_system_prompt(options)
                    .rstrip()
                    .endswith("Current working directory: /work/learn-pi")
                )

    def test_windows_cwd_is_normalised_to_forward_slashes(self) -> None:
        prompt = build_system_prompt(_base_options(cwd="C:\\work\\learn-pi"))

        self.assertIn("Current working directory: C:/work/learn-pi", prompt)

    def test_append_segment_appears_only_when_non_empty(self) -> None:
        without = build_system_prompt(_base_options())
        with_segment = build_system_prompt(_base_options(append_system_prompt="Always answer in Chinese."))

        self.assertNotIn("Always answer in Chinese.", without)
        self.assertIn("Always answer in Chinese.", with_segment)

    def test_project_context_is_injected_on_both_paths(self) -> None:
        files = (ContextFile(path="AGENTS.md", content="Keep answers short."),)

        for options in (
            _base_options(context_files=files),
            _base_options(custom_prompt="Custom persona.", context_files=files),
        ):
            with self.subTest(custom=options.custom_prompt is not None):
                prompt = build_system_prompt(options)
                self.assertIn("<project_context>", prompt)
                self.assertIn('<project_instructions path="AGENTS.md">', prompt)


class SkillInjectionTests(unittest.TestCase):
    def test_skills_are_injected_when_read_tool_is_selected(self) -> None:
        prompt = build_system_prompt(
            _base_options(
                selected_tools=("read", "write"),
                skills=(Skill(name="review", description="Review a pull request"),),
            )
        )

        self.assertIn("review", prompt)

    def test_skills_are_injected_when_only_bash_can_read_them(self) -> None:
        prompt = build_system_prompt(
            _base_options(
                selected_tools=("bash",),
                skills=(Skill(name="review", description="Review a pull request"),),
            )
        )

        self.assertIn('<skills read_with="bash">', prompt)

    def test_skills_are_dropped_without_a_tool_that_can_read_them(self) -> None:
        prompt = build_system_prompt(
            _base_options(
                selected_tools=("write",),
                skills=(Skill(name="review", description="Review a pull request"),),
            )
        )

        self.assertNotIn("<skills", prompt)
        self.assertNotIn("review", prompt)


class GuidelineTests(unittest.TestCase):
    def test_always_on_guidelines_are_present(self) -> None:
        prompt = build_system_prompt(_base_options())

        self.assertIn("Be concise in your responses", prompt)
        self.assertIn("Show file paths clearly when working with files", prompt)

    def test_powershell_changes_the_file_exploration_guideline(self) -> None:
        prompt = build_system_prompt(_base_options(selected_tools=("powershell",)))

        self.assertIn("Use PowerShell for file operations", prompt)

    def test_dedicated_search_tools_suppress_the_fallback_guideline(self) -> None:
        prompt = build_system_prompt(_base_options(selected_tools=("bash", "grep")))

        self.assertNotIn("Use bash for file operations", prompt)

    def test_guidelines_are_deduplicated(self) -> None:
        prompt = build_system_prompt(
            _base_options(prompt_guidelines=("Be concise in your responses",))
        )

        self.assertEqual(1, prompt.count("Be concise in your responses"))


class FileDiscoveryTests(unittest.TestCase):
    def test_project_file_requires_a_trusted_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "project"
            agent_dir = root / "agent"
            (cwd / CONFIG_DIR_NAME).mkdir(parents=True)
            project_file = cwd / CONFIG_DIR_NAME / "SYSTEM.md"
            project_file.write_text("project persona", encoding="utf-8")
            agent_dir.mkdir()

            self.assertIsNone(
                discover_system_prompt_file(cwd, agent_dir, project_trusted=False)
            )
            self.assertEqual(
                project_file, discover_system_prompt_file(cwd, agent_dir, project_trusted=True)
            )

    def test_global_file_does_not_require_project_trust(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "project"
            agent_dir = root / "agent"
            cwd.mkdir()
            agent_dir.mkdir()
            global_file = agent_dir / "SYSTEM.md"
            global_file.write_text("global persona", encoding="utf-8")

            self.assertEqual(
                global_file, discover_system_prompt_file(cwd, agent_dir, project_trusted=False)
            )

    def test_project_file_wins_over_global_when_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "project"
            agent_dir = root / "agent"
            (cwd / CONFIG_DIR_NAME).mkdir(parents=True)
            project_file = cwd / CONFIG_DIR_NAME / "SYSTEM.md"
            project_file.write_text("project", encoding="utf-8")
            agent_dir.mkdir()
            (agent_dir / "SYSTEM.md").write_text("global", encoding="utf-8")

            self.assertEqual(
                project_file, discover_system_prompt_file(cwd, agent_dir, project_trusted=True)
            )

    def test_no_file_means_the_hard_coded_persona_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / "project"
            agent_dir = root / "agent"
            cwd.mkdir()
            agent_dir.mkdir()

            self.assertIsNone(discover_system_prompt_file(cwd, agent_dir, project_trusted=True))


class OverrideTests(unittest.TestCase):
    def test_persona_override_replaces_the_base(self) -> None:
        self.assertEqual(
            "overridden",
            resolve_persona("base", lambda base: "overridden"),
        )

    def test_without_override_the_base_survives(self) -> None:
        self.assertEqual("base", resolve_persona("base"))

    def test_returning_none_from_an_override_falls_back_to_the_default(self) -> None:
        prompt = build_system_prompt(_base_options(custom_prompt=None))

        self.assertIn("expert coding assistant", prompt)
        self.assertIsNone(resolve_persona("base", lambda base: None))

    def test_append_override_can_clear_the_segment(self) -> None:
        self.assertEqual((), resolve_append(("rule",), lambda base: ()))

    def test_append_override_without_a_callable_keeps_the_rules(self) -> None:
        self.assertEqual(("rule",), resolve_append(("rule",)))


class DemoTests(unittest.TestCase):
    def test_demo_reports_the_path_differences(self) -> None:
        result = demo()

        self.assertTrue(result["default_has_guidelines"])
        self.assertFalse(result["custom_has_guidelines"])
        self.assertTrue(result["skills_in_default"])
        self.assertFalse(result["skills_without_read_tool"])
        self.assertTrue(result["cwd_appended_to_custom"])
        self.assertTrue(result["project_context_in_custom"])


if __name__ == "__main__":
    unittest.main()
