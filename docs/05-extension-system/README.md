# 扩展系统与工具链

Pi 扩展是 TypeScript 代码。课程在此只陈述固定基线能够支持的事件和改写边界。

## 扩展能做什么

扩展可以注册工具、命令、快捷键、UI 组件和 Provider 集成，也可以订阅生命周期事件。事件名与 payload 类型应从当前 ExtensionAPI 类型定义读取，而不是从旧示例复制。

## 容易混淆的修正

- 会话关闭事件名是 session_shutdown，不是 session_end。
- 当前没有 settings_change 事件。
- 工具调用输入的改写是在事件对象上原地进行；不存在返回 modifiedInput 的协议。
- 在压缩开始前定制行为应使用 session_before_compact。

扩展应该验证所有外部输入、限制可执行操作，并把异常变成明确的用户反馈或日志。

## 社区扩展参考

Pi 生态已有 5500+ 个扩展/技能/主题/模板包，持续更新。生态地图见 [awesome-pi](https://github.com/BubblePtr/awesome-pi)（按 Web 访问、MCP、子代理、UI、安全、记忆、上下文等分类聚合）。下面按教学价值挑选 star 较高的项目：先精读三个代表，再浏览更多高 star 项目。

### 建议精读的三个代表

#### 1. pi-llama（HuggingFace 官方，93★）— 一个 Provider 扩展的完整写法

[pi-llama](https://github.com/huggingface/pi-llama) 是单文件 `index.ts`，能在一页内读完：它从运行中的 llama-server 动态发现模型，再注册为 `llama-cpp` Provider。核心两行：

- `pi.registerProvider("llama-cpp", { name, baseUrl, apiKey, api: "openai-completions", models })` — 与课程 [09 章](../09-providers-and-models/README.md) 更新的 Provider 入口一致；
- `pi.registerCommand("llama-version", ...)` — 顺手注册一个查询命令。

```bash
pi install github.com/huggingface/pi-llama
```

#### 2. narumiruna/pi-extensions（390★）— 多包扩展仓库如何组织

[pi-extensions](https://github.com/narumiruna/pi-extensions) 是 27 个包的 TypeScript monorepo（pi-statusline、pi-plan-mode、pi-worktree、pi-lsp、pi-goal、pi-subagents、pi-sync、pi-firecrawl、pi-tui-kit 等），`docs/` 下沉淀了扩展工程约定：`extension-conventions.md`（扩展约定）、`extension-settings.md`（设置命名）、`readme-conventions.md`（README 格式）、ADR 与实现笔记。想学习多个扩展如何共享工具库、统一设置命名、用 changeset 发版，这是最佳范本。

```bash
pi install npm:@narumitw/pi-extensions
```

#### 3. pi-context-prune（214★）— 上下文/压缩类扩展

[pi-context-prune](https://github.com/championswimmer/pi-context-prune) 总结已完成的工具调用批次，把原始输出从 LLM 上下文中修剪掉，提供 5 种修剪模式。它演示的是与课程 [16 章](../16-compaction/README.md) 相同的思路——压缩是会话生命周期的一部分，要在保留因果与节省窗口之间权衡——但发生在工具调用粒度。

```bash
pi install npm:pi-context-prune
```

### 更多高 star 扩展

| 项目 | Star | 类型 | 说明 | 安装 |
| --- | --- | --- | --- | --- |
| [pi-web-access](https://github.com/nicobailon/pi-web-access) | 1190 | Web 访问 | 搜索、内容提取、YouTube 视频理解；多 Provider 降级链、GitHub 克隆、零配置 | `pi install npm:pi-web-access` |
| [pi-web](https://github.com/jmfederico/pi-web) | 593 | Web UI | 浏览器监督真实工作区中的会话，断线不杀进程，多会话并行 | `pi install npm:@jmfederico/pi-web` |
| [pi-interactive-shell](https://github.com/nicobailon/pi-interactive-shell) | 561 | 工具 + UI | PTY 交互式 CLI 控制（vim / psql / ssh / rebase），TUI overlay，用户可随时接管 | `pi install npm:pi-interactive-shell` |
| [pi-extensions](https://github.com/narumiruna/pi-extensions) | 390 | 集合 | 27 包 monorepo，覆盖状态栏、计划、worktree、LSP 等 | `pi install npm:@narumitw/pi-extensions` |
| [pi-context-prune](https://github.com/championswimmer/pi-context-prune) | 214 | 上下文 | 工具调用树剪枝、批次总结 | `pi install npm:pi-context-prune` |
| [monopi](https://github.com/ifiokjr/monopi) | 145 | 配置 | 一键安装扩展/主题/提示词/技能 bundle（“oh-my-zsh for pi”） | `pi install github.com/ifiokjr/monopi` |
| [pi-claude-cli](https://github.com/rchern/pi-claude-cli) | 98 | Provider | 把 LLM 调用路由到已认证的 Claude Code CLI | `npm:pi-claude-cli` |
| [pi-model-switch](https://github.com/nicobailon/pi-model-switch) | 93 | 命令 | 让 Agent 自己切换模型 | `pi install npm:pi-model-switch` |
| [pi-llama](https://github.com/huggingface/pi-llama) | 93 | Provider | llama.cpp Provider，动态发现模型 | `pi install github.com/huggingface/pi-llama` |
| [awesome-pi](https://github.com/BubblePtr/awesome-pi) | 92 | 生态 | 5500+ 包的分类聚合列表 | — |

### 边界与阅读建议

- **以固定基线为准**：社区项目随 Pi 版本演进，具体事件名、payload、返回约定以 0.84.2 基线的 `extensions.md` 与 ExtensionAPI 类型定义为准，不要从旧 README 复制事件名。
- **star 不代表质量**：安装第三方扩展前先读源码，确认它请求的权限、网络行为与数据去向，只安装可信来源。
- **与课程实验无关**：这些是 TypeScript 生产扩展，本课程的 [Python 对照实验](#python-对照实验) 不绑定、也不依赖任何 Pi 扩展。

## Python 对照实验

[extension_events.py](../../learn_pi_lab/labs/extension_events.py) 演示按注册顺序派发、异常隔离、可重复取消订阅与深度快照：

    python3 -m learn_pi_lab lab events
    python3 -m unittest tests.test_07_extension_events -v

这是课程自己的事件总线，不是 Pi ExtensionAPI 的 Python 绑定。
