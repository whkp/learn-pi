# Provider 与模型 —— 一行代码驾驭多个模型

> Provider 层要回答三个问题：有哪些模型（元数据）、怎么调用（API 类型）、凭什么授权（认证）。Pi 的核心设计是**三者分离**：模型选择器只读元数据，实际调用走统一流式接口，认证由运行时按 Provider 解析——因此"不能仅按模型字符串推断权限或费用"。

## 学习目标

- 理解 Provider 注册表如何组织"认证 + API 类型 + 模型元数据"。
- 看懂 models.json 的结构：providers 是对象映射、api 决定协议。
- 理解两种注册形态：完整 Provider vs 名 + 配置。

## Pi 的核心设计

### 元数据、协议、认证三者分离

| 维度 | 回答 | 例子 |
|------|------|------|
| 元数据 | 有哪些模型 | id、显示名、contextWindow、reasoning、cost |
| API 类型 | 怎么调用 | openai-completions、anthropic-messages、google-generative-ai |
| 认证 | 凭什么授权 | 订阅 OAuth、API key、环境变量 |

三者分离的意义：`/model` 只读元数据；切换模型时重新检查上下文窗口与工具支持；认证来源（`/login` 的 auth.json、环境变量、`--api-key`）独立于模型选择。`contextWindow`、`reasoning`、`cost` 是相互独立的维度——显示名相近的模型，能力可能完全不同。

### 两种注册形态

扩展注册 Provider 有两种方式：

- **完整 Provider 对象**：自定义认证、过滤、刷新、流式行为——深度定制时用。
- **provider 名 + 配置**：只覆盖 baseUrl / apiKey / api / models——对接 OpenAI 兼容服务器等常见场景。

### models.json：providers 是映射不是列表

用户自定义模型写在 `~/.pi/agent/models.json`，每次打开 `/model` 时重载（无需重启）：

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [
        { "id": "llama3.1:8b", "name": "Llama 3.1 8B", "contextWindow": 128000 }
      ]
    }
  }
}
```

要点：`api` 决定协议（可设在 provider 层默认、model 层覆盖）；`apiKey` 可以是占位符（本地服务器忽略 key，但 pi 仍按"需要认证"处理模型）；对不支持 `developer` role 的服务器用 `compat.supportsDeveloperRole: false` 降级。

## 当前 Pi 行为

- 订阅 Provider：Claude Pro/Max、ChatGPT Plus/Pro（Codex）、GitHub Copilot、OpenRouter；API Key Provider：Anthropic、OpenAI、Google、DeepSeek、Mistral、Groq、Kimi、MiniMax、小米 MiMo 等。
- 自定义 Provider 当前入口：`pi.registerProvider(...)` 配 pi-ai 的 `createProvider` 与 `api`（如 `openAICompletionsApi()`）；`streamSimple` 已移到 compat 包，是兼容导出。
- 未配置认证的模型会加载但不出现 `/model`，直到有可用认证。

## 在 Pi 里怎么操作

- `/login`：选择并登录 Provider（订阅 OAuth 或写 API Key 到 `~/.pi/agent/auth.json`）。
- `/model`：打开模型选择器；`/logout`：清除已存凭据。
- 自定义 Provider/模型写入 `~/.pi/agent/models.json`；环境变量方式如 `export ANTHROPIC_API_KEY=...`。

## Python 实验

[provider_registry.py](../../learn_pi_lab/labs/provider_registry.py) 只保存非敏感元数据（不读环境变量、不调用 Provider），拒绝重复模型，提供稳定排序目录：

```python
registry = ProviderRegistry()
registry.register("openai-completions", "demo-1", "Demo Model", 128_000)
selection = registry.select("openai-completions", "demo-1")
# catalog() 按 (provider_id, model_id) 排序返回不可变目录
```

教学点：注册表把"标识合法性、重复检测、排序目录"做成一件事，与 Pi 的 `model-registry.ts` 职责同构；`_validate_identifier` 用正则约束 provider/model id，防止用不可靠的标识做 key。Tau 的 `tau_coding/provider_catalog.py` 则是内置目录（导入期加载），回答同一个问题：运行时从哪里知道有哪些 Provider。

```sh
python3 -m learn_pi_lab lab providers
```

## 验证方式

```sh
python3 -m unittest tests.test_08_provider_registry -v
```

## 边界与安全

- 凭据从来不应写进课程示例、日志或版本库；为每个 Provider 使用最小范围凭据。
- 模型显示名/上下文窗口/API 类型不能互相推断；本地模型（Ollama）的 key 是占位符，不代表真实认证。
