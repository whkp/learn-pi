# Prompt Templates 提示词模板

> 提示词模板是可复用的 Markdown 片段，通过 `/名称` 快速展开为完整提示。

---

## 一、模板概览

### 1.1 什么是提示词模板？

提示词模板是预定义的提示词，保存为 Markdown 文件。通过 `/名称` 快速调用，避免重复输入。

### 1.2 模板位置

| 位置 | 作用域 |
|------|--------|
| `~/.pi/agent/prompts/*.md` | 全局 |
| `.pi/prompts/*.md` | 项目级 |
| `prompts/` 目录（包内） | 包内 |
| `--prompt-template <路径>` | CLI 参数 |

### 1.3 禁用发现

```bash
pi --no-prompt-templates
```

---

## 二、模板格式

### 2.1 基本结构

```markdown
---
description: 审查暂存的 git 变更
---
审查暂存的变更（`git diff --cached`）。重点关注：
- Bug 和逻辑错误
- 安全问题
- 错误处理缺口
```

### 2.2 Frontmatter

| 字段 | 说明 |
|------|------|
| `description` | 模板描述（可选） |
| `argument-hint` | 参数提示（可选） |

- 文件名即命令名：`review.md` → `/review`
- 如果没有 `description`，第一行非空行作为描述

### 2.3 参数提示

```markdown
---
description: 审查 PR
argument-hint: "<PR-URL>"
---
```

在自动补全中显示：

```
→ pr   <PR-URL>       — 审查 PR
  is   <issue>        — 分析 GitHub Issue
  wr   [instructions] — 完成当前任务
```

---

## 三、使用模板

### 3.1 基本使用

在编辑器中输入 `/`，然后选择模板：

```
/review                           # 展开 review.md
/component Button                 # 展开并传参
/component Button "click handler" # 多个参数
```

### 3.2 参数传递

模板支持位置参数：

| 变量 | 说明 |
|------|------|
| `$1`, `$2`, ... | 位置参数 |
| `$@` 或 `$ARGUMENTS` | 所有参数（连接） |
| `${@:N}` | 从第 N 个位置开始的参数 |
| `${@:N:L}` | 从第 N 个位置开始的 L 个参数 |

### 3.3 示例

**模板文件：** `component.md`

```markdown
---
description: 创建 React 组件
---
创建一个名为 $1 的 React 组件，功能：$@
```

**使用：**

```
/component Button "onClick handler" "disabled support"
```

**展开后：**

```
创建一个名为 Button 的 React 组件，功能：onClick handler disabled support
```

---

## 四、常用模板示例

### 4.1 代码审查

```markdown
---
description: 审查代码变更
argument-hint: "[file-pattern]"
---
审查最近的代码变更。重点关注：
- 代码质量和可读性
- 潜在 Bug
- 安全问题
- 性能问题

如果提供了文件模式，只审查匹配的文件。
```

### 4.2 提交信息

```markdown
---
description: 生成 Git 提交信息
---
根据 `git diff --cached` 生成规范的提交信息。

格式：
- 类型：feat/fix/docs/style/refactor/test/chore
- 简短描述（中文，50 字以内）
- 详细说明（如有必要）
```

### 4.3 测试生成

```markdown
---
description: 为文件生成测试
argument-hint: "<file>"
---
为 $1 生成单元测试。

要求：
- 覆盖主要功能
- 测试边界情况
- 使用描述性测试名称
- 遵循项目测试风格
```

### 4.4 文档生成

```markdown
---
description: 为代码生成文档
argument-hint: "<file-or-function>"
---
为 $1 生成详细的 API 文档。

包括：
- 功能描述
- 参数说明
- 返回值
- 使用示例
- 注意事项
```

### 4.5 重构建议

```markdown
---
description: 分析代码并提供重构建议
argument-hint: "<file>"
---
分析 $1 并提供重构建议。

关注：
- 代码重复
- 函数过长
- 命名不清晰
- 设计模式应用
```

---

## 五、高级用法

### 5.1 多行参数

```
/component Button "
  onClick handler
  disabled support
  loading 状态
"
```

### 5.2 引用文件

```
/review @src/app.ts @src/app.test.ts
```

### 5.3 结合管道

```bash
cat README.md | pi -p @review-prompt.md
```

---

## 六、最佳实践

1. **清晰的描述**：让 LLM 理解模板用途
2. **合理的参数**：使用 `argument-hint` 提示参数
3. **简洁的模板**：避免过长的模板
4. **参数化**：使用变量让模板更灵活
5. **文档化**：为团队模板添加说明

---

## 七、模板发现

Pi 递归发现 `prompts/` 目录下的所有 `.md` 文件。如果需要子目录中的模板，通过 `prompts` 设置或包清单显式添加。

---

## 八、小结

| 功能 | 说明 |
|------|------|
| **快速调用** | `/名称` 展开模板 |
| **参数支持** | `$1`, `$2`, `$@` 等 |
| **参数提示** | `argument-hint` 显示参数说明 |
| **自动补全** | 输入 `/` 时显示可用模板 |
| **多位置** | 全局、项目级、包内 |

---

## 下一步

掌握了提示词模板后，下一章我们将介绍 [主题与 UI 定制](../13-themes-and-ui/README.md)，学习如何美化 Pi 的界面。
