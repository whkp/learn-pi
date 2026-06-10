# 桌面端设计方案

> 探讨如何基于 Pi 构建跨平台桌面应用。

---

## 一、需求分析

### 1.1 核心功能

| 功能 | 说明 |
|------|------|
| **项目选择** | 打开本机目录，记住最近项目 |
| **对话交互** | 会话列表、对话窗、可复制/引用 |
| **工具可视化** | 展示工具调用输入/输出、耗时、状态 |
| **变更预览** | 文件 diff/patch 预览与应用/撤销 |
| **终端/日志** | 展示引擎日志、调试信息 |
| **模型配置** | Provider/Model 选择、API Key 安全存储 |

### 1.2 非功能需求

| 需求 | 说明 |
|------|------|
| **安全** | 文件读写与命令执行需授权 |
| **跨平台** | macOS/Windows/Linux 统一体验 |
| **可观测性** | 本地日志、崩溃报告 |
| **更新分发** | 安装包、自动更新 |

---

## 二、架构方案

### 2.1 三层架构

```
┌─────────────────────────────────────────┐
│           Desktop Shell（桌面壳）         │
│  窗口、菜单、通知、自动更新、Keychain      │
├─────────────────────────────────────────┤
│              UI（前端）                  │
│  聊天、diff、tool timeline、设置页        │
├─────────────────────────────────────────┤
│            Engine（Pi 引擎）             │
│  agent loop、tool 执行、skills 加载       │
└─────────────────────────────────────────┘
```

### 2.2 通信模式

- **UI ↔ Shell**：IPC（Electron IPC / Tauri invoke）
- **Shell ↔ Engine**：
  - 同进程（import SDK）
  - 子进程（stdio JSON-RPC、WebSocket）

---

## 三、方案对比

### 3.1 Electron + Node 内嵌

```
Electron 主进程
├── Renderer（UI）
└── Node Worker（Pi SDK）
```

**优点**：
- 最快落地
- 调试简单
- 复用率高

**缺点**：
- 安全边界弱
- 性能/内存开销大

### 3.2 Electron + Engine 子进程（推荐）

```
Electron 主进程
├── Renderer（UI）
└── Engine Daemon（子进程）
    └── Pi 引擎（stdio/WebSocket 通信）
```

**优点**：
- 安全/稳定性更好
- 更易做权限控制
- 引擎可替换

**缺点**：
- 集成复杂度更高
- 调试链更长

### 3.3 Tauri + Node sidecar

```
Tauri（Rust 壳）
├── Web UI（React/Vue）
└── Node sidecar（Pi 引擎）
```

**优点**：
- 体积小、启动快
- 安全模型更严格

**缺点**：
- 工程复杂度高
- 三栈并行（Rust + Node + 前端）

### 3.4 纯 Web UI

```
浏览器
└── Web 应用
    └── Pi 服务（localhost）
```

**优点**：
- 实现成本最低
- 跨平台天然

**缺点**：
- 桌面集成弱
- 用户体验不如原生

---

## 四、推荐方案

### 4.1 决策矩阵

| 维度 | Electron 同进程 | Electron 子进程 | Tauri | Web |
|------|-----------------|-----------------|-------|-----|
| 落地速度 | **最快** | 快 | 中 | **最快** |
| 安全隔离 | 中 | **高** | **高** | 中 |
| 体积性能 | 中 | 中 | **优** | 取决于浏览器 |
| 可维护性 | 中 | **高** | 中-高 | 中 |
| 产品化潜力 | 高 | **最高** | 高 | 中 |

### 4.2 推荐路径

- **MVP**：Electron 同进程 或 Web+localhost
- **产品化**：Electron 子进程（推荐）
- **强安全/小体积**：Tauri + Node sidecar

---

## 五、关键技术

### 5.1 权限与安全

- **工作区限制**：所有文件操作限制在 workspaceRoot 内
- **命令执行策略**：高危命令阻断、需用户确认、审计日志
- **网络访问策略**：web-fetch 工具可开关、域名白名单

### 5.2 Skills 管理

- 支持 `--no-skills` 模式
- 按 workspace 的 skill profile
- 每个 skill 给出来源与启用状态

### 5.3 Diff/Patch

- 引擎输出结构化 patch（unified diff）
- UI 展示：按文件、按 hunk
- 支持：逐文件应用、逐 hunk 应用、全部撤销

### 5.4 密钥管理

- macOS：Keychain
- Windows：Credential Manager
- Linux：Secret Service

---

## 六、分阶段计划

### Phase 0：技术验证（1-2 周）

- 选 Electron
- 最小 UI：聊天 + 选择文件夹
- 引擎用 CLI 子进程（stdio）
- 跑通：发消息 → tool call → 展示结果

### Phase 1：MVP（3-6 周）

- 会话管理、聊天历史
- tool timeline
- diff/patch 预览
- 权限提示

### Phase 2：可用产品（6-10 周）

- Keychain
- 自动更新
- 崩溃恢复/引擎重启
- 插件化与 skill profile

---

## 七、协议草案

```typescript
export type EngineEvent =
  | { type: "assistant.delta"; sessionId: string; text: string }
  | { type: "tool.call"; sessionId: string; callId: string; name: string; input: unknown }
  | { type: "tool.result"; sessionId: string; callId: string; ok: boolean; output: string }
  | { type: "patch"; sessionId: string; patch: string };

export interface EngineApi {
  start(input: { workspaceRoot: string; config: unknown }): Promise<{ version: string }>
  createSession(): Promise<{ sessionId: string }>
  send(sessionId: string, message: string): AsyncIterable<EngineEvent>
  approveToolCall(callId: string): Promise<void>
  denyToolCall(callId: string): Promise<void>
}
```

---

## 八、小结

| 方案 | 适用场景 |
|------|----------|
| **Electron 同进程** | MVP、快速验证 |
| **Electron 子进程** | 产品化（推荐） |
| **Tauri** | 强安全、小体积 |
| **Web** | 内部工具、快速验证 |

---

## 下一步

了解了桌面端设计后，下一章我们将进入 [实战项目](../19-real-projects/README.md)，通过实际项目巩固所学知识。
