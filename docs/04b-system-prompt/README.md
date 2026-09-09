# 系统提示词 —— 每轮请求的第一个决定

> 模型每一轮收到的第一条消息都是 system。它决定"模型是谁、能用什么、该怎么说话"。这件事**完全由 harness 决定**，模型只是接收方。本章拆开 Pi 拼装这条消息的每一段，看清哪些能换、哪些能关、哪些根本关不掉。

## 学习目标

- 说出系统提示词的五段拼装及其顺序，并解释为什么顺序是有意义的。
- 区分 `customPrompt` 路径与默认路径：前者会**跳过**工具说明、指南和文档指针。
- 掌握人设的三级回退链，以及项目级文件为何需要"项目信任"。
- 判断每一段能否被关闭，并说出"关不掉"的那一段要用什么手段改写。
- 用离线 Python 实验复现拼装结果，并解释技能段在什么条件下会被自动丢弃。

## 一、问题：能力边界写在第一条消息里

[01 章](../01-architecture/README.md)说过：**智能来自模型，能力边界全来自 harness**。系统提示词就是这句话最直接的证据。

同一个模型——同一个版本、同一个 API Key——给它两段不同的 system 消息：

| system 消息 | 模型的表现 |
|---|---|
| 通用编程助手 + 工具清单 + 文件操作规范 | 读代码、改文件、跑测试，删东西前先问 |
| 数据分析师 + 业务规则 + 输出格式 | 先确认已知/未知，给可能原因排序，不编造数据 |

模型没变，变的是 harness 塞进去的那段文字。所以系统提示词不是"开场白"，它是**运行时配置**——是 harness 把产品决策翻译成模型能理解的语言的地方。

这也意味着一个常见误解是错的：**换人设不等于换模型**。你不需要微调、不需要换 Provider，只需要改这一段字符串。

## 二、五段拼装：顺序与来源

Pi 最终发出的系统提示词由五段按固定顺序拼接而成：

```text
最终提示词 = ① 人设          ← 模型是谁
           + ② 追加规则      ← 在人设后追加的几条
           + ③ 项目上下文    ← 从 AGENTS.md / CLAUDE.md 读
           + ④ 技能摘要      ← 从 .pi/skills/*/SKILL.md 读
           + ⑤ 工作目录      ← SDK 固定追加的一行
```

逐段看它们从哪来、能不能关：

| 段 | 来源 | 在 `customPrompt` 路径下 | 能否关闭 |
|---|---|---|---|
| ① 人设 | `customPrompt` / `SYSTEM.md` / 硬编码 | 变成你给的字符串，且**不再拼工具清单与指南** | 能替换，不能删除 |
| ② 追加规则 | `APPEND_SYSTEM.md` / `appendSystemPromptOverride` | 仍然追加 | 能清空 |
| ③ 项目上下文 | 从 `cwd` 向上逐级找 `AGENTS.md` / `CLAUDE.md` | 仍然追加 | 不创建文件即为空 |
| ④ 技能摘要 | `{cwd}/.pi/skills/` 与全局 skills 目录 | 仍然追加 | 无 `read`/`bash` 工具时自动丢弃 |
| ⑤ 工作目录 | SDK 无条件追加 `Current working directory: ...` | 仍然追加 | **没有开关**，只能用扩展钩子改写 |

顺序不是随意的。人设放最前面，因为它是模型读到的第一印象；工作目录放最后，因为它是一条随时可变的运行环境事实，而不是角色定义。

## 三、两条路径：`customPrompt` 与默认路径

这是本章最容易踩的坑。

`buildSystemPrompt` 内部是**两条完全不同的分支**。当调用方传入 `customPrompt` 时，函数走进简化分支：

```text
customPrompt 分支：
  ① 你的字符串
+ ② 追加规则
+ ③ 项目上下文
+ ④ 技能摘要
+ ⑤ 工作目录
```

而默认分支会额外拼出三段内容：

```text
默认分支：
  ① 硬编码人设 "You are an expert coding assistant operating inside pi..."
    + Available tools:  ← 只有提供了 toolSnippets 的工具才出现
    + Guidelines:       ← 按所选工具动态生成
    + Pi documentation: ← pi 文档路径指针
+ ② ... ⑤ 同上
```

**所以"传了 customPrompt"并不等于"只换了人设"。** 工具清单、行为指南、Pi 文档指针全部消失。这在两种场景下后果截然不同：

- **做垂直智能体**（客服、分析师）——正好，你本来就不想要"用 bash 列文件"这种指南。
- **只是想加几句规则**——错路。你应该用 `appendSystemPromptOverride` 或 `APPEND_SYSTEM.md`，保留默认人设和工具说明。

判断标准很简单：**你要不要丢弃"这是个编程 Agent"的整套默认行为？** 要丢弃就用 `customPrompt`，不想丢弃就走追加。

### 工具清单是动态生成的

默认路径下，`Available tools` 只列出**调用方同时提供了 `toolSnippets` 条目**的工具。也就是说，工具注册了不等于模型看得见——还得给它一句一行描述。`visibleTools` 为空时，清单渲染成 `(none)`。

`Guidelines` 同样是算出来的：文件探索指南会根据工具集变化——有 `bash` 但没 `grep`/`find`/`ls` 时提示"用 bash 做 ls/rg/find"；0.85 起若只有 `powershell`，措辞会改成 PowerShell。最后无条件加上两条：`Be concise in your responses` 和 `Show file paths clearly when working with files`。指南会去重。

## 四、人设的三级回退链

人设不是只有一个来源，而是一条带回退的链：

| 优先级 | 来源 | 位置 |
|---|---|---|
| 1（最高） | `systemPromptOverride` | 代码层，函数返回什么就是什么 |
| 2 | `{cwd}/.pi/SYSTEM.md`（项目级）或 `~/.pi/agent/SYSTEM.md`（全局级） | 文件层 |
| 3（兜底） | 硬编码 `You are an expert coding assistant...` | SDK 内 |

前两级都没有时，才回退到第 3 级。这就是为什么做垂直智能体**必须主动换掉人设**——你什么都不做，拿到的就是编程助手。

### 项目级文件需要"项目信任"

这一条很容易被忽略：`{cwd}/.pi/SYSTEM.md` 只有在 `isProjectTrusted()` 为真时才生效。原因很直接——项目目录里的文件可能来自任何地方，如果克隆一个仓库就能悄悄改写你的 Agent 人设，那是个安全问题。全局 `~/.pi/agent/SYSTEM.md` 不需要这个检查，因为它已经在你的用户目录下。

实践建议：**优先用项目级 `.pi/SYSTEM.md`（可版本化、随仓库走），不要用全局级**。全局文件会影响你机器上所有 Pi 项目，难追踪也难管理。

### 追加规则怎么清空

`appendSystemPromptOverride` 收到的是 `string[]`，返回 `[]` 就能清空这一整段：拼接后长度为 0，等价于没有追加规则。这在把通用编程助手改造成垂直智能体时几乎是必需动作——否则 `APPEND_SYSTEM.md` 里的编程规范可能残留。

## 五、那一行为什么关不掉

`Current working directory: /your/cwd` 是 SDK **无条件追加**的，没有任何配置项能关掉它。

对垂直智能体来说它基本无害（客服、翻译不会因此出错），但对两类场景有影响：

- 不想让模型看到真实路径（比如多租户服务里路径含用户信息）；
- 提示词需要严格可复现（路径变化导致 prompt 变化，缓存和回放全部失效）。

要改它，只能走扩展的 `before_agent_start` 钩子：系统提示词发给模型前会经过它，handler 返回 `{ systemPrompt }` 即可替换本轮内容。注意这不影响工具的真实执行目录——那是 SDK 按 `cwd` 配置解析的，跟模型看不看得到这行无关。

## 当前 Pi 行为

以下均为固定基线 Pi 0.85.1 @ `d981de1229ef899957bbe968bc8dcda02a21f477` 的实测事实。

- `buildSystemPrompt(options)` 位于 `packages/coding-agent/src/core/system-prompt.ts`，五段拼装顺序如上。
- `customPrompt` 分支不生成 `Available tools`、`Guidelines`、`Pi documentation` 三段。
- 文件探索指南按工具集分支；0.85.1 支持 `powershell`（0.84.3 新增的可选 Windows 工具），并与 `bash` 组合出三种措辞。
- 技能摘要注入条件在 0.85.1 放宽为工具集含 `read` **或** `bash`；0.84.2 只认 `read`。`formatSkillsForPrompt` 也因此多接收一个"用哪个工具读"的参数。
- `systemPromptOverride` 与 `appendSystemPromptOverride` 的签名在 `resource-loader.ts` 第 192、193 行，应用位置在第 528、540–541 行。
- `discoverSystemPromptFile()`（第 1025 行）与 `discoverAppendSystemPromptFile()`（第 1037 行）先查项目级（需 `isProjectTrusted()`）、再查全局级。
- `Current working directory` 无条件追加，没有关闭开关。

### 源码证据表

| 教学结论 | Pi 路径 | 符号 / 位置 |
|---|---|---|
| 五段拼装顺序 | `src/core/system-prompt.ts` | `buildSystemPrompt()` |
| customPrompt 走简化分支 | `src/core/system-prompt.ts` | `if (customPrompt)` |
| 工具清单需 toolSnippets | `src/core/system-prompt.ts` | `visibleTools` |
| 指南按工具集动态生成 | `src/core/system-prompt.ts` | `hasBash` / `hasPowerShell` / `addGuideline()` |
| 技能需 read 或 bash | `src/core/system-prompt.ts` | `skillFileReadTool` |
| 人设覆盖链 | `src/core/resource-loader.ts` | 192–193（签名）、528、540–541（应用） |
| SYSTEM.md 发现 | `src/core/resource-loader.ts` | `discoverSystemPromptFile()` 1025 |
| APPEND_SYSTEM.md 发现 | `src/core/resource-loader.ts` | `discoverAppendSystemPromptFile()` 1037 |
| 技能与提示词模板覆盖 | `src/core/resource-loader.ts` | `skillsOverride` 177、`promptsOverride` 181 |

## Python 实验

课程的 [system_prompt.py](../../learn_pi_lab/labs/system_prompt.py) 用同一套分段实现拼装，跑起来能直接看到两条路径的差别：

```sh
python3 -m learn_pi_lab lab system-prompt
```

输出里同时给出拼装结果和一组断言：

```text
default_has_guidelines: true      # 默认路径拼了 Guidelines
custom_has_guidelines: false      # customPrompt 路径没有
skills_in_default: true           # 有 read 工具，技能段注入
skills_without_read_tool: false   # 只有 write，技能段被丢弃
cwd_appended_to_custom: true      # cwd 无条件追加，关不掉
project_context_in_custom: true   # 项目上下文在两条路径都注入
```

模块里可以直接调用的几个入口：

```python
from learn_pi_lab.labs.system_prompt import (
    ContextFile, Skill, SystemPromptOptions, build_system_prompt,
)

prompt = build_system_prompt(
    SystemPromptOptions(
        cwd="/work/learn-pi",
        custom_prompt="你是一个企业数据分析助手。",
        append_system_prompt="",
        context_files=(ContextFile(path="AGENTS.md", content="回答用中文。"),),
        skills=(Skill(name="review", description="评审一次改动"),),
    )
)
assert "Guidelines:" not in prompt          # custom 分支没有指南
assert "Current working directory" in prompt  # cwd 仍然在
```

## 失败与边界实验

三种典型误用，都可以在上面的实验里复现：

1. **以为只换了人设，其实丢了工具说明。** 传 `custom_prompt` 后再检查 `Available tools:` —— 它不在了。模型不知道自己有哪些工具，工具调用率会掉。修法：需要工具说明就别用 `customPrompt`，改用追加规则。
2. **技能段悄悄消失。** 把 `selected_tools` 设成 `("write",)`，技能摘要不见了。原因是模型没有能读取技能文件的工具，注入了也读不到，于是干脆不注入。修法：工具集里保留 `read` 或 `bash`。
3. **项目级 `SYSTEM.md` 不生效。** 文件明明存在却不生效，通常是项目未被信任。这是安全设计而非 bug：克隆来的仓库不该能改写你的 Agent 人设。修法：确认项目信任状态，或改用全局文件/代码层覆盖。

> 这一模块的核心代码在[核心代码导览 · 系统提示词拼装](../code-tour.md)有逐段解读。

## 验证方式

```sh
python3 -m learn_pi_lab lab system-prompt
python3 -m unittest tests.test_14_system_prompt -v
python3 scripts/check_course_contract.py
```

测试覆盖了五段顺序、两条路径差异、cwd 无条件追加、Windows 路径规范化、技能丢弃条件、指南去重与 PowerShell 措辞、文件发现的信任要求，以及覆盖链。

## 边界与安全

- **系统提示词不是安全边界。** 它能约束模型倾向，但模型可以被用户输入诱导偏离。真正的权限、路径隔离、命令白名单必须在产品层实现（见 [03 章工具系统](../03-tools/README.md)）。
- **项目级提示词文件是供应链风险。** 这正是 `isProjectTrusted()` 存在的原因。评审第三方仓库时，`.pi/SYSTEM.md`、`.pi/APPEND_SYSTEM.md`、`AGENTS.md` 都应被视为可执行配置，而不是文档。
- **提示词里不要放密钥。** 系统提示词会随每轮请求发送、会进会话记录、可能被压缩进摘要。参见 [07 章上下文压缩](../07-context-and-compaction/README.md) 关于敏感信息传播的部分。
- **工作目录那一行会泄露路径。** 多租户或共享服务场景需要脱敏时，用扩展钩子改写，而不是假设有开关。
- 本课程的 Python 教学模型只复现分段与条件，**不是** Pi 的 TypeScript 生产实现，也不读取真实文件系统。

## 回顾

- **系统提示词 = 运行时配置**：它定义模型是谁、能用什么、怎么说话，由 harness 全权决定。
- **五段拼装**：人设 → 追加规则 → 项目上下文 → 技能摘要 → 工作目录。
- **两条路径**：`customPrompt` 会连工具说明和指南一起丢掉，不只是换人设。
- **三级回退**：代码层覆盖 > 文件层 `SYSTEM.md`（项目级需信任）> 硬编码兜底。
- **`cwd` 那一行关不掉**，只能靠扩展钩子改写。

下一章回到状态本身——[会话管理](../05-sessions/README.md)：这些每轮都要重发的提示词，与持久化的对话历史如何分工。
