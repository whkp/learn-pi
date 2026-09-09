"""A course-local system-prompt assembly teaching model.

This mirrors the *structure* of Pi 0.85.1's ``buildSystemPrompt`` and the
prompt-override chain in ``DefaultResourceLoader``.  It is not Pi's production
implementation and not a compatible API: Pi builds its prompt in TypeScript and
pulls documentation paths, skills and context files from the real filesystem.
The teaching model keeps every segment explicit so a reader can see what is
concatenated, in which order, and under which condition.

Signatures of interest in the pinned baseline (tag v0.85.1):

* ``packages/coding-agent/src/core/system-prompt.ts``
  ``buildSystemPrompt(options)`` -- the five-segment assembly.
* ``packages/coding-agent/src/core/resource-loader.ts``
  ``systemPromptOverride`` (interface line 192, applied line 528) and
  ``appendSystemPromptOverride`` (line 193, applied lines 540-541).
  ``discoverSystemPromptFile()`` (line 1025) and
  ``discoverAppendSystemPromptFile()`` (line 1037) resolve the file layer.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

#: Directory name for project-local Pi configuration, e.g. ``{cwd}/.pi``.
CONFIG_DIR_NAME: Final = ".pi"

#: The hard-coded persona used when nothing else supplies one.
DEFAULT_PERSONA: Final = (
    "You are an expert coding assistant operating inside pi, a coding agent harness."
)

#: Tools assumed when the caller does not select an explicit set.
DEFAULT_TOOLS: Final[tuple[str, ...]] = ("read", "bash", "edit", "write")

#: Tools that can read a skill file.  0.85.1 accepts either; 0.84.2 only read.
SKILL_READ_TOOLS: Final[tuple[str, ...]] = ("read", "bash")

#: Guidelines appended to every default prompt, in this order.
ALWAYS_GUIDELINES: Final[tuple[str, ...]] = (
    "Be concise in your responses",
    "Show file paths clearly when working with files",
)


@dataclass(frozen=True)
class ContextFile:
    """One project instruction block injected as ``<project_instructions>``."""

    path: str
    content: str


@dataclass(frozen=True)
class Skill:
    """A discoverable skill whose description may be summarised into the prompt."""

    name: str
    description: str


@dataclass(frozen=True)
class SystemPromptOptions:
    """Every input ``build_system_prompt`` reads, with the same defaults as Pi."""

    cwd: str
    custom_prompt: str | None = None
    selected_tools: tuple[str, ...] = DEFAULT_TOOLS
    tool_snippets: Mapping[str, str] | None = None
    prompt_guidelines: tuple[str, ...] = ()
    append_system_prompt: str = ""
    context_files: tuple[ContextFile, ...] = ()
    skills: tuple[Skill, ...] = ()


def build_system_prompt(options: SystemPromptOptions) -> str:
    """Assemble the system prompt exactly in Pi's segment order.

    Segments, for both the custom-prompt path and the default path:

    1. persona -- ``custom_prompt`` when given, otherwise the hard-coded persona
       plus the tools list, the guidelines, and the documentation pointers;
    2. ``append_system_prompt`` -- only when non-empty;
    3. project context files -- only when non-empty;
    4. skills -- only when some tool in :data:`SKILL_READ_TOOLS` is selected;
    5. the current working directory line, appended unconditionally.

    The documentation pointers live inside the default persona block in Pi, so
    the teaching model keeps them folded into segment 1 rather than inventing a
    sixth segment.
    """
    prompt_cwd = options.cwd.replace("\\", "/")
    append_section = f"\n\n{options.append_system_prompt}" if options.append_system_prompt else ""
    snippets = options.tool_snippets or {}
    tools = options.selected_tools or DEFAULT_TOOLS
    skill_read_tool = next((name for name in SKILL_READ_TOOLS if name in tools), None)

    if options.custom_prompt:
        prompt = options.custom_prompt
        prompt += append_section
        prompt += _project_context_section(options.context_files)
        if skill_read_tool and options.skills:
            prompt += _skills_section(options.skills, skill_read_tool)
        prompt += f"\nCurrent working directory: {prompt_cwd}\n"
        return prompt

    visible = [name for name in tools if snippets.get(name)]
    tools_list = (
        "\n".join(f"- {name}: {snippets[name]}" for name in visible) if visible else "(none)"
    )
    guidelines = _guidelines_block(tools, options.prompt_guidelines)

    prompt = (
        f"{DEFAULT_PERSONA}\n\n"
        f"Available tools:\n{tools_list}\n\n"
        f"Guidelines:\n{guidelines}"
    )
    prompt += append_section
    prompt += _project_context_section(options.context_files)
    if skill_read_tool and options.skills:
        prompt += _skills_section(options.skills, skill_read_tool)
    prompt += f"\nCurrent working directory: {prompt_cwd}"
    return prompt


def _project_context_section(context_files: Sequence[ContextFile]) -> str:
    """Render segment 3, or an empty string when there is nothing to inject."""
    if not context_files:
        return ""
    body = "".join(
        f'<project_instructions path="{item.path}">\n{item.content}\n</project_instructions>\n\n'
        for item in context_files
    )
    return f"\n\n<project_context>\n\nProject-specific instructions and guidelines:\n\n{body}</project_context>\n"


def _skills_section(skills: Sequence[Skill], read_tool: str) -> str:
    """Render segment 4. Reaching a skill file requires a tool that can read it."""
    lines = "\n".join(f"- {skill.name}: {skill.description}" for skill in skills)
    return f"\n\n<skills read_with=\"{read_tool}\">\n{lines}\n</skills>\n"


def _guidelines_block(tools: Sequence[str], extra: Sequence[str]) -> str:
    """Build the guideline bullets, de-duplicated and order-stable."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add(guideline: str) -> None:
        normalized = guideline.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)

    has_bash = "bash" in tools
    has_powershell = "powershell" in tools
    has_grep = "grep" in tools
    has_find = "find" in tools
    has_ls = "ls" in tools

    if (has_bash or has_powershell) and not has_grep and not has_find and not has_ls:
        if has_bash and has_powershell:
            add(
                "Use bash or PowerShell for file operations like listing, "
                "searching, and finding files"
            )
        elif has_powershell:
            add("Use PowerShell for file operations like listing, searching, and finding files")
        else:
            add("Use bash for file operations like ls, rg, find")

    for guideline in extra:
        add(guideline)
    for guideline in ALWAYS_GUIDELINES:
        add(guideline)

    return "\n".join(f"- {item}" for item in ordered)


def discover_system_prompt_file(
    cwd: Path,
    agent_dir: Path,
    project_trusted: bool,
) -> Path | None:
    """Resolve the file layer of the persona fallback chain.

    Pi checks the project-level ``{cwd}/.pi/SYSTEM.md`` only when the project is
    trusted, then falls back to the global ``~/.pi/agent/SYSTEM.md``.  When
    neither exists the hard-coded persona is used.
    """
    project_path = cwd / CONFIG_DIR_NAME / "SYSTEM.md"
    if project_trusted and project_path.exists():
        return project_path
    global_path = agent_dir / "SYSTEM.md"
    if global_path.exists():
        return global_path
    return None


#: A persona override receives the resolved base and returns the replacement.
SystemPromptOverride = Callable[[str | None], str | None]
AppendOverride = Callable[[tuple[str, ...]], tuple[str, ...]]


def resolve_persona(
    base: str | None,
    override: SystemPromptOverride | None = None,
) -> str | None:
    """Apply the code-layer override; it wins over every file-layer source."""
    return override(base) if override else base


def resolve_append(
    base: tuple[str, ...],
    override: AppendOverride | None = None,
) -> tuple[str, ...]:
    """Apply the append-rule override. Returning ``()`` clears the segment."""
    return override(base) if override else base


def demo() -> dict[str, object]:
    """Return a fixed, offline comparison of the assembly paths."""
    default_options = SystemPromptOptions(
        cwd="/work/learn-pi",
        tool_snippets={"read": "Read a file", "bash": "Run a command"},
        context_files=(ContextFile(path="AGENTS.md", content="Keep answers short."),),
        skills=(Skill(name="review", description="Review a pull request"),),
    )
    custom_options = SystemPromptOptions(
        cwd="/work/learn-pi",
        custom_prompt="You are a data analysis assistant.",
        context_files=default_options.context_files,
        skills=default_options.skills,
    )
    no_read_tools_options = SystemPromptOptions(
        cwd="/work/learn-pi",
        selected_tools=("write",),
        skills=default_options.skills,
    )

    default_prompt = build_system_prompt(default_options)
    custom_prompt = build_system_prompt(custom_options)
    no_read_prompt = build_system_prompt(no_read_tools_options)

    return {
        "default_prompt": default_prompt,
        "custom_prompt": custom_prompt,
        "default_has_guidelines": "Guidelines:" in default_prompt,
        "custom_has_guidelines": "Guidelines:" in custom_prompt,
        "skills_in_default": "<skills" in default_prompt,
        # write-only tool sets cannot reach a skill file, so the segment is dropped
        "skills_without_read_tool": "<skills" in no_read_prompt,
        "cwd_appended_to_custom": custom_prompt.rstrip().endswith(
            "Current working directory: /work/learn-pi"
        ),
        "project_context_in_custom": "<project_context>" in custom_prompt,
    }
