# 安装与快速上手

> 从零开始，快速上手 Pi 编码智能体。

---

## 一、环境要求

- **Node.js**：v18 或更高版本
- **npm**：v8 或更高版本
- **终端**：支持 ANSI 转义序列的现代终端

### 推荐终端

| 终端 | 平台 | 推荐度 |
|------|------|--------|
| Ghostty | macOS/Linux | ⭐⭐⭐⭐⭐ |
| iTerm2 | macOS | ⭐⭐⭐⭐ |
| WezTerm | 跨平台 | ⭐⭐⭐⭐ |
| Windows Terminal | Windows | ⭐⭐⭐ |
| tmux | 跨平台 | ⭐⭐⭐ |

---

## 二、安装 Pi

### 方式一：npm 安装（推荐）

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

`--ignore-scripts` 禁用安装脚本，Pi 正常运行不需要它们。

### 方式二：curl 安装

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

### 验证安装

```bash
pi --version
```

### 卸载

```bash
# npm 安装
npm uninstall -g @earendil-works/pi-coding-agent

# pnpm
pnpm remove -g @earendil-works/pi-coding-agent

# Yarn
yarn global remove @earendil-works/pi-coding-agent

# Bun
bun uninstall -g @earendil-works/pi-coding-agent
```

卸载后，设置、凭证、会话和已安装的包仍保留在 `~/.pi/agent/`。

---

## 三、认证配置

### 方式一：OAuth 登录（推荐）

```bash
pi
/login
```

然后选择提供商：
- **Claude Pro/Max**：Anthropic 订阅
- **ChatGPT Plus/Pro (Codex)**：OpenAI 订阅
- **GitHub Copilot**：GitHub 订阅

### 方式二：API Key

```bash
# 设置环境变量
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GEMINI_API_KEY=...
export DEEPSEEK_API_KEY=sk-...
export XIAOMI_API_KEY=...

# 启动 pi
pi
```

或者通过 `/login` 选择 API Key 提供商，密钥会保存到 `~/.pi/agent/auth.json`。

### 方式三：auth.json

直接编辑 `~/.pi/agent/auth.json`：

```json
{
  "anthropic": { "type": "api_key", "key": "sk-ant-..." },
  "openai": { "type": "api_key", "key": "sk-..." },
  "deepseek": { "type": "api_key", "key": "sk-..." }
}
```

---

## 四、第一个会话

### 4.1 启动 Pi

```bash
cd /path/to/your/project
pi
```

### 4.2 输入请求

在编辑器中输入：

```
帮我分析这个项目的结构
```

按 Enter 发送。Pi 会：
1. 读取项目文件
2. 分析目录结构
3. 给出结构说明

### 4.3 常用操作

| 操作 | 方式 |
|------|------|
| 参考文件 | 输入 `@` 模糊搜索，或 `@README.md` |
| 多行输入 | Shift+Enter |
| 运行命令 | `!npm run lint` |
| 粘贴图片 | Ctrl+V |
| 切换模型 | `/model` 或 Ctrl+L |
| 切换思考级别 | Shift+Tab |

---

## 五、项目指令

### 5.1 创建 AGENTS.md

在项目根目录创建 `AGENTS.md`：

```markdown
# 项目指令

- 代码修改后运行 `npm run check`
- 保持回复简洁
- 使用 TypeScript 严格模式
- 遵循 ESLint 规范
```

Pi 启动时会自动加载这个文件。

### 5.2 指令文件位置

Pi 按顺序加载以下位置的指令文件：

1. `~/.pi/agent/AGENTS.md`（全局）
2. 父目录（从当前目录向上遍历）
3. 当前目录

所有匹配的文件会被拼接在一起。

### 5.3 禁用指令加载

```bash
pi --no-context-files
# 或
pi -nc
```

---

## 六、非交互模式

### 6.1 Print 模式

```bash
# 一次性查询
pi -p "总结这个代码库"

# 管道输入
cat README.md | pi -p "总结这个文本"

# 图片分析
pi -p @screenshot.png "这张图片里有什么？"
```

### 6.2 JSON 模式

```bash
pi --mode json "列出所有 TypeScript 文件"
```

输出结构化的 JSON 事件流，便于程序解析。

### 6.3 RPC 模式

```bash
pi --mode rpc
```

用于进程间通信，通过 stdin/stdout 交换 JSONL 消息。

---

## 七、常用配置

### 7.1 全局设置

编辑 `~/.pi/agent/settings.json`：

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-20250514",
  "defaultThinkingLevel": "medium",
  "theme": "dark"
}
```

### 7.2 项目设置

编辑 `.pi/settings.json`（项目级覆盖全局）：

```json
{
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384
  }
}
```

### 7.3 通过命令修改

```bash
/model          # 切换模型
/settings       # 打开设置界面
/compact        # 手动压缩上下文
```

---

## 八、常见问题

### Q: 启动时报 "API key not found"

A: 确保设置了正确的环境变量，或通过 `/login` 配置认证。

### Q: 工具执行超时

A: 检查网络连接，或在设置中调整超时时间：
```json
{
  "retry": {
    "provider": {
      "timeoutMs": 3600000
    }
  }
}
```

### Q: 上下文用尽

A: 使用 `/compact` 压缩上下文，或调整压缩设置：
```json
{
  "compaction": {
    "enabled": true,
    "keepRecentTokens": 20000
  }
}
```

### Q: 如何使用国产模型？

A: 设置对应的 API Key：
```bash
export XIAOMI_API_KEY=your-key
export DEEPSEEK_API_KEY=your-key
export KIMI_API_KEY=your-key
```

---

## 九、小结

| 步骤 | 命令 |
|------|------|
| 安装 | `npm install -g @earendil-works/pi-coding-agent` |
| 认证 | `/login` 或设置环境变量 |
| 启动 | `pi` |
| 使用 | 输入请求，按 Enter |
| 继续 | `pi -c` |

---

## 下一步

成功安装并运行 Pi 后，下一章我们将详细介绍 [交互模式](../07-interactive-mode/README.md)，掌握所有编辑器功能和快捷键。
