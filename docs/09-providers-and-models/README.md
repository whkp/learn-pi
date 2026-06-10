# Provider 与模型配置

> Pi 支持 20+ LLM 提供商，让你灵活选择最适合的模型。

---

## 一、Provider 概览

### 1.1 认证方式

| 方式 | 说明 |
|------|------|
| **OAuth 订阅** | Claude Pro/Max、ChatGPT Plus/Pro、GitHub Copilot |
| **API Key** | 环境变量或 auth.json |
| **云服务** | Azure OpenAI、AWS Bedrock、Google Vertex |

### 1.2 支持的 Provider

| 类型 | Provider |
|------|----------|
| 订阅 | Anthropic、OpenAI (Codex)、GitHub Copilot |
| API Key | Anthropic、OpenAI、DeepSeek、Google Gemini、Mistral、Groq、Cerebras、xAI、OpenRouter 等 |
| 云服务 | Azure OpenAI、AWS Bedrock、Google Vertex |
| 国产 | 小米 MiMo、Kimi、MiniMax |

---

## 二、认证配置

### 2.1 OAuth 登录

```bash
pi
/login
```

选择提供商，按照提示完成认证。

### 2.2 环境变量

```bash
# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
export OPENAI_API_KEY=sk-...

# Google
export GEMINI_API_KEY=...

# DeepSeek
export DEEPSEEK_API_KEY=sk-...

# 小米 MiMo
export XIAOMI_API_KEY=...

# Kimi
export KIMI_API_KEY=...

# Mistral
export MISTRAL_API_KEY=...

# Groq
export GROQ_API_KEY=...

# xAI
export XAI_API_KEY=...

# OpenRouter
export OPENROUTER_API_KEY=...

# Hugging Face
export HF_TOKEN=...
```

### 2.3 auth.json

编辑 `~/.pi/agent/auth.json`：

```json
{
  "anthropic": { "type": "api_key", "key": "sk-ant-..." },
  "openai": { "type": "api_key", "key": "sk-..." },
  "deepseek": { "type": "api_key", "key": "sk-..." },
  "google": { "type": "api_key", "key": "..." },
  "xiaomi": { "type": "api_key", "key": "..." }
}
```

auth.json 优先级高于环境变量。

---

## 三、模型切换

### 3.1 交互式切换

- **Ctrl+L**：打开模型选择器
- **/model**：同上

### 3.2 快速循环

- **Ctrl+P**：下一个模型
- **Shift+Ctrl+P**：上一个模型

### 3.3 命令行指定

```bash
pi --model claude-sonnet-4-20250514 "帮我分析代码"
pi --provider openai --model gpt-4o "帮我分析代码"
pi --model openai/gpt-4o "帮我分析代码"  # 使用 provider/model 格式
```

### 3.4 指定思考级别

```bash
pi --thinking high "解决这个复杂问题"
pi --model sonnet:high "解决这个复杂问题"  # 使用 model:thinking 格式
```

### 3.5 配置循环模型

在 `settings.json` 中：

```json
{
  "enabledModels": ["claude-*", "gpt-4o", "gemini-2*"]
}
```

或使用 `/scoped-models` 在交互中管理。

---

## 四、思考级别

### 4.1 级别说明

| 级别 | 说明 |
|------|------|
| `off` | 不显示思考过程 |
| `minimal` | 最小思考 |
| `low` | 低度思考 |
| `medium` | 中等思考（默认） |
| `high` | 高度思考 |
| `xhigh` | 极高思考 |

### 4.2 切换方式

- **Shift+Tab**：循环切换
- `/settings`：在设置中选择
- `--thinking <级别>`：启动时指定

### 4.3 自定义预算

```json
{
  "thinkingBudgets": {
    "minimal": 1024,
    "low": 4096,
    "medium": 10240,
    "high": 32768
  }
}
```

---

## 五、自定义 Provider

### 5.1 通过 models.json

编辑 `~/.pi/agent/models.json`：

```json
{
  "providers": [
    {
      "id": "my-provider",
      "name": "My Provider",
      "api": "openai",
      "baseUrl": "https://my-api.com/v1",
      "models": [
        {
          "id": "my-model",
          "name": "My Model",
          "contextWindow": 128000,
          "maxTokens": 4096
        }
      ]
    }
  ]
}
```

### 5.2 通过扩展

```typescript
pi.registerProvider("my-provider", {
  name: "My Provider",
  models: [
    { id: "my-model-1", name: "My Model 1" }
  ],
  stream: async (request) => {
    // 实现流式调用
  }
});
```

---

## 六、模型配置

### 6.1 默认模型

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-20250514"
}
```

### 6.2 列出可用模型

```bash
pi --list-models
pi --list-models claude  # 搜索包含 claude 的模型
```

---

## 七、多 Provider 策略

### 7.1 场景切换

不同场景使用不同模型：

```json
{
  "enabledModels": [
    "claude-sonnet-4-20250514",  // 日常开发
    "gpt-4o",                     // 代码补全
    "deepseek-chat",              // 中文任务
    "gemini-2*"                   // 长上下文
  ]
}
```

### 7.2 成本控制

- 使用 `gpt-4o-mini` 处理简单任务
- 使用 `claude-sonnet-4-20250514` 处理复杂任务
- 使用 `deepseek-chat` 处理中文任务

---

## 八、常见问题

### Q: 切换模型后工具调用失败

A: 确保新模型支持工具调用。不是所有模型都支持。

### Q: 如何使用本地模型？

A: 通过自定义 Provider 接入 Ollama、vLLM 等本地服务。

### Q: API Key 安全吗？

A: auth.json 文件权限为 0600（仅用户可读写）。建议定期轮换密钥。

---

## 九、小结

| 功能 | 操作 |
|------|------|
| OAuth 登录 | `/login` |
| 设置 API Key | 环境变量或 auth.json |
| 切换模型 | Ctrl+L 或 `/model` |
| 指定模型 | `--model <模型>` |
| 指定思考级别 | `--thinking <级别>` |
| 配置循环模型 | `enabledModels` 设置 |

---

## 下一步

配置好 Provider 后，下一章我们将介绍 [Skills 技能系统](../10-skills-system/README.md)，学习如何使用和创建技能。
