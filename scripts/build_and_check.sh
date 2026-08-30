#!/usr/bin/env bash
# Learn Pi — 一键检查与站点构建
#
# 在干净 checkout 中执行单条命令即可完成全部验证：
#   docs/ 是单一事实源 → 生成站点源 → 契约检查 → 链接检查 → 单元测试 → mdBook 构建
#
# 用法：
#   ./scripts/build_and_check.sh          # 全部检查 + 构建
#   ./scripts/build_and_check.sh --skip-build   # 只检查，不构建站点

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_BUILD=0
if [[ "${1:-}" == "--skip-build" ]]; then
  SKIP_BUILD=1
fi

fail() {
  echo "✗ FAIL: $*" >&2
  exit 1
}

echo "==> [1/5] 生成站点源（docs → src + SUMMARY.md）"
python3 scripts/build_site.py || fail "build_site.py 失败"

echo "==> [2/5] 课程契约检查"
python3 scripts/check_course_contract.py || fail "课程契约检查失败"

echo "==> [3/5] Markdown 链接检查"
python3 scripts/check_markdown_links.py || fail "链接检查失败"

echo "==> [4/5] 单元测试"
python3 -m unittest discover -s tests -v >/dev/null 2>&1 || fail "单元测试失败"

if [[ "$SKIP_BUILD" -eq 1 ]]; then
  echo "✓ 检查全部通过（已跳过站点构建）"
  exit 0
fi

echo "==> [5/5] mdBook 构建"
if ! command -v mdbook >/dev/null 2>&1; then
  fail "未找到 mdbook，请先安装：brew install mdbook"
fi
mdbook build || fail "mdBook 构建失败"

echo ""
echo "✓ 全部通过：契约、链接、测试、站点构建"
echo "  站点输出：book/（或推送到 GitHub 由 CI 发布）"
