#!/usr/bin/env python3
"""Generate the mdBook site source for Learn Pi.

Copies ``docs/`` into ``src/`` (the mdBook source root), rewrites
repository-internal file links (``../../learn_pi_lab/...``) to GitHub blob
URLs so they work on the published site, and writes ``src/SUMMARY.md``.

Usage::

    python3 scripts/build_site.py
    mdbook build

Run this before ``mdbook build``; ``docs/`` remains the single source of truth.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SRC = ROOT / "src"
GITHUB_BLOB = "https://github.com/whkp/learn-pi/blob/main"

# (src-relative path, 侧边栏标题) —— 顺序即阅读顺序
CHAPTERS = [
    ("00-course-map.md", "课程地图"),
    ("01-architecture/README.md", "01 架构总览"),
    ("02-agent-loop/README.md", "02 Agent Loop"),
    ("03-tools/README.md", "03 工具系统"),
    ("04-messages-and-memory/README.md", "04 消息与记忆"),
    ("05-sessions/README.md", "05 会话管理"),
    ("06-events-and-extensions/README.md", "06 事件驱动与扩展"),
    ("07-context-and-compaction/README.md", "07 上下文压缩"),
    ("08-providers-and-models/README.md", "08 Provider 与模型"),
    ("09-reliability/README.md", "09 可靠性"),
    ("10-protocol-and-integration/README.md", "10 协议与集成"),
    ("11-projects-and-evaluation/README.md", "11 实战与评测"),
    ("glossary.md", "术语表"),
    ("pi-source-map.md", "Pi 源码映射"),
]

# 仓库内文件链接：../../learn_pi_lab/labs/mini_agent.py → GitHub blob URL
REPO_LINK = re.compile(r"\.\./\.\./(learn_pi_lab|projects|scripts|tests)/[A-Za-z0-9_./\-]+")


def _rewrite_repo_links(match: re.Match[str]) -> str:
    return f"{GITHUB_BLOB}/{match.group(0)[6:]}"  # 去掉前导 ../../


def main() -> None:
    if SRC.exists():
        shutil.rmtree(SRC)

    # 1. 复制 docs/ → src/，跳过无关内容
    shutil.copytree(DOCS, SRC, ignore=shutil.ignore_patterns("__pycache__", "superpowers"))

    # 2. 改写仓库内文件链接为 GitHub blob URL
    for markdown in SRC.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        rewritten = REPO_LINK.sub(_rewrite_repo_links, text)
        if rewritten != text:
            markdown.write_text(rewritten, encoding="utf-8")

    # 3. 生成 SUMMARY.md
    summary_lines = ["# Learn Pi", ""]
    for path, title in CHAPTERS:
        summary_lines.append(f"- [{title}]({path})")
    (SRC / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"site source generated at {SRC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
