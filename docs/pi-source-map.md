# Pi 源码映射

<!-- pi-baseline: version=0.85.1 commit=d981de1229ef899957bbe968bc8dcda02a21f477 -->

这份映射固定课程讨论所依据的 Pi 基线。后续章节会将具体行为链接到该基线中的源文件和符号；未列出映射时，不应把旧文档或 Python 教学模型描述为当前 Pi 行为。

## 使用约定

- `当前 Pi 行为` 小节只陈述此固定基线能够支持的事实。
- `Python 实验` 小节使用课程本地接口，并明确它不是 Pi 的 TypeScript 生产 API。
- 更新基线时，同时更新映射、课程章节和契约测试。
- Python 成品参考实现是 Tau（tau_agent / tau_ai / tau_coding）；它镜像 Pi 的设计，可作为阅读教学的对照，但不是 Pi SDK。

## 主题到源码入口

下列路径相对 Pi 仓库根目录（tag v0.85.1）。它们是核对课程内容的起点，而不是复制进本仓库的第二份 API 文档。

| 主题 | 优先阅读的固定基线路径 |
| --- | --- |
| 安装、命令和上下文文件 | packages/coding-agent/docs/quickstart.md、usage.md、settings.md |
| 会话、JSONL 和分支 | packages/coding-agent/docs/sessions.md、session-format.md |
| 扩展与压缩 hook | packages/coding-agent/docs/extensions.md、compaction.md、src/core/extensions/types.ts |
| 技能、提示词、主题和包 | packages/coding-agent/docs/skills.md、prompt-templates.md、themes.md、packages.md |
| 模型和自定义 Provider | packages/coding-agent/docs/models.md、custom-provider.md、src/core/model-registry.ts |
| SDK、RPC 与 JSON 输出 | packages/coding-agent/docs/sdk.md、rpc.md、json.md、src/core/sdk.ts |
| 工具创建与 cwd | packages/coding-agent/src/core/tools/index.ts |
| 安全与容器化 | packages/coding-agent/docs/security.md、containerization.md、environment-variables.md |
| 系统提示词拼装 | packages/coding-agent/src/core/system-prompt.ts |
| 资源加载与提示词覆盖 | packages/coding-agent/src/core/resource-loader.ts |
| 提示词模板 | packages/coding-agent/src/core/prompt-templates.ts |

## 当前包拓扑

Pi 0.85.1 Monorepo 的核心包仍是 ai（pi-ai）、agent（pi-agent-core）、tui（pi-tui）、coding-agent（pi-coding-agent）。

实验性包（API 可能变化，不构成稳定契约）：client、protocol（CBOR 二进制协议）、server（PiServer 会话服务）、evals、telemetry、session-backends，以及 0.85 新增的 **chord**。

chord 的目标是用作与具体应用无关的基础设施：插件的加载/组合/卸载/重载与打包、本地与远程服务的声明与消费、对称 RPC 传输、以及权威最新值状态到本地与远程消费者的复制。它的 `PLANNING.md` 明确写着**尚不是稳定的公开 API 契约**，课程因此只把它登记为实验性包，不作为教学内容。

课程不把旧图中的 pi-web-ui 当作当前包。

## 常见误解与基线事实

这一节不是本仓库的历史错误记录，而是读者最容易从外部带入的误解——旧教程、旧版本 README 或生成内容里的编造项。每条以固定基线源码为准；踩中任何一条，轻则代码不工作，重则对机制形成错误心智模型。

- **Provider 适配**：旧教程里的 `streamSimple()` 已移入 `@earendil-works/pi-ai/compat`，属兼容导出，不再是首选入口；当前入口是 `pi.registerProvider()` 配 `createProvider` 与 `api`（如 `openAICompletionsApi()`）。
- **扩展关闭事件**：是 `session_shutdown`，不是 `session_end`，也不存在 `settings_change`。
- **工具输入改写**：改写发生在事件对象上，handler 不返回 `modifiedInput`——按返回值改写不会生效。
- **SDK 订阅**：是 `session.subscribe(...)`，不是 `session.on(...)`；`createCodingTools` 必须传 `cwd`。
- **会话命令**：`/tree` 用于会话树导航与分支，`/export` 才生成 HTML，两者职责不同；会话格式为 JSONL v3。
- **prompts 目录**：发现是非递归的；压缩的扩展边界是 `session_before_compact`。
- **安装**：需要 Node.js >=22.19.0；用 `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`（跳过安装脚本是有意为之），官方文档站点是 pi.dev。
- **技能注入**：技能注册了不等于会注入提示词——工具集里必须有能读取技能文件的 `read` 或 `bash`（0.85.1 起放宽；0.84.2 只认 `read`）。
- **PowerShell 工具**：0.84.3 起存在可选的 Windows 原生 PowerShell 执行工具，`buildSystemPrompt` 的文件探索指南会据此改写措辞——按旧版本资料写 bash-only 的结论已过时。
- **项目级提示词文件**：`{cwd}/.pi/SYSTEM.md` 与 `APPEND_SYSTEM.md` 文件存在不等于生效，还需要项目被信任（`isProjectTrusted()`）；全局 `~/.pi/agent/` 下的同名文件不需要项目信任。

返回 [课程地图](00-course-map.md)。
