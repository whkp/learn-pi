#!/usr/bin/env bash
# Learn Pi — 一键检查与站点构建
#
# 在干净 checkout 中执行单条命令即可完成全部验证：
#   docs/ 是单一事实源 → 契约检查 → 链接检查 → 单元测试 → 静态站点构建
#
# 用法：
#   ./scripts/build_and_check.sh               # 全部检查 + 构建
#   ./scripts/build_and_check.sh --skip-build  # 只检查，不构建站点

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_BUILD=0
if [[ "${1:-}" == "--skip-build" ]]; then
  SKIP_BUILD=1
fi

PYTHON="${PYTHON:-python3}"

fail() {
  echo "✗ FAIL: $*" >&2
  exit 1
}

echo "==> [1/4] 课程契约检查"
"$PYTHON" scripts/check_course_contract.py || fail "课程契约检查失败"

echo "==> [2/4] Markdown 链接检查"
"$PYTHON" scripts/check_markdown_links.py || fail "链接检查失败"

echo "==> [3/4] 单元测试"
"$PYTHON" -m unittest discover -s tests >/dev/null 2>&1 || fail "单元测试失败"

if [[ "$SKIP_BUILD" -eq 1 ]]; then
  echo "✓ 检查全部通过（已跳过站点构建）"
  exit 0
fi

echo "==> [4/4] 静态站点构建（docs → dist）"
if ! command -v node >/dev/null 2>&1; then
  fail "未找到 node，请先安装 Node.js 20 或更高版本"
fi
if [[ ! -d node_modules ]]; then
  echo "    未发现 node_modules，先安装依赖…"
  npm ci || fail "依赖安装失败"
fi
node site/build.mjs || fail "站点构建失败"

echo ""
echo "✓ 全部通过：契约、链接、测试、站点构建"
echo "  站点输出：dist/（推送到 GitHub 后由 CI 发布）"
