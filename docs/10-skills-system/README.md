# Skills 技能系统

> 技能是按需加载的能力包，为特定任务提供专业化的工作流、脚本和文档。

---

## 一、技能概览

### 1.1 什么是技能？

技能是一个自包含的能力包，包含：
- **指令**：告诉 Agent 如何完成特定任务
- **脚本**：辅助执行的脚本文件
- **文档**：参考文档和 API 说明

### 1.2 技能发现

Pi 采用渐进式披露策略：
1. 启动时只加载技能的名称和描述
2. 当任务匹配时，Agent 自动加载完整指令
3. 也可以通过 `/skill:name` 手动加载

---

## 二、技能位置

### 2.1 加载路径

| 位置 | 作用域 |
|------|--------|
| `~/.pi/agent/skills/` | 全局 |
| `~/.agents/skills/` | 全局 |
| `.pi/skills/` | 项目级 |
| `.agents/skills/` | 项目级 |
| `skills/` 目录（包内） | 包内 |
| `--skill <路径>` | CLI 参数 |

### 2.2 禁用发现

```bash
pi --no-skills
```

---

## 三、技能结构

### 3.1 目录结构

```
my-skill/
├── SKILL.md              # 必需：指令文件
├── scripts/              # 辅助脚本
│   └── process.sh
├── references/           # 参考文档
│   └── api-reference.md
└── assets/               # 资源文件
    └── template.json
```

### 3.2 SKILL.md 格式

````markdown
---
name: my-skill
description: 这个技能做什么，什么时候使用。要具体。
---

# My Skill

## 设置

首次使用前运行：
```bash
cd /path/to/skill && npm install
```

## 使用

```bash
./scripts/process.sh <input>
```
````

### 3.3 Frontmatter

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 是 | 最多 64 字符，小写字母、数字、连字符 |
| `description` | 是 | 最多 1024 字符，说明技能功能和使用场景 |
| `license` | 否 | 许可证 |
| `compatibility` | 否 | 环境要求 |

---

## 四、使用技能

### 4.1 自动加载

当任务匹配技能描述时，Agent 会自动加载完整指令。

### 4.2 手动加载

```
/skill:my-skill
/skill:my-skill 附加参数
```

### 4.3 技能命令

技能自动注册为 `/skill:name` 命令。在 `settings.json` 中可以禁用：

```json
{
  "enableSkillCommands": false
}
```

---

## 五、常用技能

### 5.1 官方技能

| 技能 | 来源 | 说明 |
|------|------|------|
| brave-search | Pi Skills | 网页搜索和内容提取 |
| transcribe | Pi Skills | 音频转录 |
| docx/pdf/pptx/xlsx | Anthropic Skills | 文档处理 |

### 5.2 从 Claude Code 迁移

在 `settings.json` 中添加 Claude Code 的技能目录：

```json
{
  "skills": [
    "~/.claude/skills",
    "~/.codex/skills"
  ]
}
```

项目级：

```json
{
  "skills": ["../.claude/skills"]
}
```

---

## 六、创建技能

### 6.1 基本步骤

1. 创建技能目录
2. 编写 SKILL.md
3. 添加脚本和文档
4. 放置到技能目录

### 6.2 示例：代码审查技能

```
code-review/
├── SKILL.md
└── scripts/
    └── review.sh
```

**SKILL.md：**

````markdown
---
name: code-review
description: 审查代码质量、安全性和性能。使用场景：代码审查、PR 审查。
---

# 代码审查

## 审查要点

1. **代码质量**
   - 命名规范
   - 函数长度
   - 代码重复

2. **安全性**
   - 输入验证
   - SQL 注入
   - XSS 防护

3. **性能**
   - 时间复杂度
   - 内存使用
   - 数据库查询

## 使用

```bash
./scripts/review.sh <file>
```
````

### 6.3 最佳实践

1. **清晰的描述**：让 Agent 理解何时使用
2. **具体的指令**：不要模糊不清
3. **相对路径**：引用脚本和文档时使用相对路径
4. **渐进加载**：只在需要时加载完整指令

---

## 七、技能验证

Pi 会验证技能是否符合 [Agent Skills 标准](https://agentskills.io/specification)：

- 名称超过 64 字符：警告
- 名称包含无效字符：警告
- 描述超过 1024 字符：警告
- 缺少描述：不加载

名称冲突（同名技能从不同位置加载）：警告，保留第一个找到的。

---

## 八、技能仓库

### 8.1 官方仓库

- [Anthropic Skills](https://github.com/anthropics/skills) - 文档处理、Web 开发
- [Pi Skills](https://github.com/badlogic/pi-skills) - 网页搜索、浏览器自动化、Google API、转录

### 8.2 安装技能

通过 pi 包安装：

```bash
pi install npm:pi-skills
```

或直接复制到技能目录。

---

## 九、小结

| 功能 | 说明 |
|------|------|
| **渐进加载** | 只加载描述，按需加载指令 |
| **自动发现** | 从多个目录自动发现技能 |
| **手动加载** | `/skill:name` 手动触发 |
| **标准验证** | 符合 Agent Skills 标准 |
| **迁移支持** | 可使用 Claude Code 技能 |

---

## 下一步

掌握了技能系统后，下一章我们将介绍 [Extensions 扩展开发](../11-extensions-development/README.md)，学习如何用 TypeScript 定制 Pi 的行为。
