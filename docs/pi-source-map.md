# Pi 源码映射

<!-- pi-baseline: version=0.75.3 commit=144b93861f339ce353531f6873d377a1e4b2f5c4 -->

这份映射固定课程讨论所依据的 Pi 基线。后续章节会将具体行为链接到该基线中的源文件和符号；未列出映射时，不应把旧文档或 Python 教学模型描述为当前 Pi 行为。

## 使用约定

- `当前 Pi 行为` 小节只陈述此固定基线能够支持的事实。
- `Python 实验` 小节使用课程本地接口，并明确它不是 Pi 的 TypeScript 生产 API。
- 更新基线时，同时更新映射、课程章节和契约测试。

## 主题到源码入口

下列路径相对 Pi 仓库根目录。它们是核对课程内容的起点，而不是复制进本仓库的第二份 API 文档。

| 主题 | 优先阅读的固定基线路径 |
| --- | --- |
| 安装、命令和上下文文件 | packages/coding-agent/docs/quickstart.md、usage.md、settings.md |
| 会话、JSONL 和分支 | packages/coding-agent/docs/sessions.md、session-format.md |
| 扩展与压缩 hook | packages/coding-agent/docs/extensions.md、compaction.md、src/core/extensions/types.ts |
| 技能、提示词、主题和包 | packages/coding-agent/docs/skills.md、prompt-templates.md、themes.md、packages.md |
| 模型和自定义 Provider | packages/coding-agent/docs/models.md、custom-provider.md、src/core/model-registry.ts |
| SDK、RPC 与 JSON 输出 | packages/coding-agent/docs/sdk.md、rpc.md、json.md、src/core/sdk.ts |
| 工具创建与 cwd | packages/coding-agent/src/core/tools/index.ts |

## 已校正的易错点

- 包拓扑是 ai、agent、tui、coding-agent；没有当前的 pi-web-ui 包。
- 扩展关闭事件是 session_shutdown；没有 settings_change。
- 工具输入改写发生在事件对象上，不返回 modifiedInput。
- SDK 订阅使用 session.subscribe；createCodingTools 需要 cwd。
- 会话为 JSONL v3；/tree 用于会话树导航，/export 才生成 HTML。
- prompts 目录发现是非递归的；压缩的扩展边界是 session_before_compact。

返回 [课程地图](00-course-map.md)。
