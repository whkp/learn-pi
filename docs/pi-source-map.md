# Pi 源码映射

<!-- pi-baseline: version=0.84.2 commit=914cf1472e715297caa30db4b9535d534a9eb718 -->

这份映射固定课程讨论所依据的 Pi 基线。后续章节会将具体行为链接到该基线中的源文件和符号；未列出映射时，不应把旧文档或 Python 教学模型描述为当前 Pi 行为。

## 使用约定

- `当前 Pi 行为` 小节只陈述此固定基线能够支持的事实。
- `Python 实验` 小节使用课程本地接口，并明确它不是 Pi 的 TypeScript 生产 API。
- 更新基线时，同时更新映射、课程章节和契约测试。
- Python 成品参考实现是 Tau（tau_agent / tau_ai / tau_coding）；它镜像 Pi 的设计，可作为阅读教学的对照，但不是 Pi SDK。

## 主题到源码入口

下列路径相对 Pi 仓库根目录（tag v0.84.2）。它们是核对课程内容的起点，而不是复制进本仓库的第二份 API 文档。

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

## 当前包拓扑

Pi 0.84.2 Monorepo 的核心包仍是 ai（pi-ai）、agent（pi-agent-core）、tui（pi-tui）、coding-agent（pi-coding-agent）。0.81 之后新增的实验性包包括 client、protocol（CBOR 二进制协议）、server（PiServer 会话服务）、evals、telemetry、session-backends；它们标注为实验性，API 可能变化。课程不把旧图中的 pi-web-ui 当作当前包。

## 已校正的易错点

- 核心包拓扑是 ai、agent、tui、coding-agent；client、protocol、server 等是实验性新增包。
- 自定义 Provider 的当前入口是 `pi.registerProvider()`，配 pi-ai 的 `createProvider` 与 `api`（如 `openAICompletionsApi()`）；`streamSimple` 已移到 `@earendil-works/pi-ai/compat`，属于兼容导出，不再是首选适配入口。
- 扩展关闭事件是 session_shutdown；没有 settings_change。
- 工具输入改写发生在事件对象上，不返回 modifiedInput。
- SDK 订阅使用 session.subscribe；createCodingTools 需要 cwd。
- 会话为 JSONL v3；/tree 用于会话树导航，/export 才生成 HTML。
- prompts 目录发现是非递归的；压缩的扩展边界是 session_before_compact。
- Pi 需要 Node.js >=22.19.0；安装用 `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`，官方文档站点是 pi.dev。

返回 [课程地图](00-course-map.md)。
