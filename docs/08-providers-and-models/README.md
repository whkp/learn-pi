# Provider 与模型 —— 一行代码驾驭多个模型

> Agent 需要同时面对多家 LLM：认证方式不同、API 格式不同、模型元数据不同。这一章拆解 Provider 层"如何实现"：统一注册、元数据模型、认证分离，以及 models.json 的完整 schema。

## 学习目标

- 理解 Provider 注册表如何把"认证 + API 类型 + 模型元数据"组织成统一结构。
- 看懂 models.json 的完整 schema：providers 对象、api 类型、模型字段。
- 理解模型显示名、上下文窗口、API 类型是不同维度，不能互相推断。
- 读 Pi 0.84.2 的模型注册实现，并对照本课程的 Python 教学模型。

## 机制：注册表 + 元数据，而不是硬编码

Provider 层要回答三个问题：

1. **有哪些模型？** —— 元数据（id、显示名、上下文窗口、能力）来自注册表/目录。
2. **怎么调用？** —— API 类型（anthropic-messages、openai-completions 等）决定请求格式。
3. **凭什么授权？** —— 认证来源（订阅 OAuth / API key / 环境变量）独立于模型选择。

三者分离的意义：模型选择器（`/model`）只读元数据；实际调用走统一的流式接口；认证由运行时按 Provider 解析。这也是课程反复强调"不能仅按模型字符串推断权限或费用"的原因——`contextWindow`、`reasoning`、`cost` 都是独立的元数据维度。

### 两种注册形态

Provider 可以以两种形态注册：

- **完整 Provider 对象**：自定义认证、过滤、刷新、流式行为——需要深度定制时用。
- **provider 名 + 配置**：只覆盖 baseUrl / apiKey / api / models 的简写形态——对接 OpenAI 兼容服务器等常见场景时用。

## Pi 源码怎么实现（0.84.2）

模型注册在 `packages/coding-agent/src/core/model-registry.ts`：

```typescript
// packages/coding-agent/src/core/model-registry.ts（Pi 0.84.2，节选）
registerProvider(provider: Provider): void;
registerProvider(providerName: string, config: ProviderConfigInput): void;
registerProvider(providerOrName: Provider | string, config?: ProviderConfigInput): void {
  // 两种重载：完整 Provider 对象，或 provider 名 + 配置
}
unregisterProvider(providerName: string): void {
  this.runtime.unregisterProvider(providerName);
}
```

### models.json 完整 schema

用户自定义模型写在 `~/.pi/agent/models.json`，每次打开 `/model` 时重载（编辑后无需重启）：

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [
        {
          "id": "llama3.1:8b",
          "name": "Llama 3.1 8B (Local)",
          "reasoning": false,
          "input": ["text"],
          "contextWindow": 128000,
          "maxTokens": 32000,
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        }
      ]
    }
  }
}
```

要点：

- **`providers` 是以标识为键的对象映射，不是列表**——课程 [01 章](../01-architecture/README.md) 之后你可以在 `model-registry.ts` 里验证这一点。
- **`api` 决定协议**：`openai-completions`（最兼容）、`openai-responses`、`anthropic-messages`、`google-generative-ai`。`api` 可设在 provider 层（默认）或 model 层（覆盖）。
- **`apiKey` 值可以是占位符**（如 `"ollama"`）：本地服务器可能忽略 key，但 pi 仍按"需要认证"处理模型，所以占位 + `/login` 存 key，或 `--api-key` 传入。
- **`compat` 字段**：对不支持 `developer` role 或 `reasoning_effort` 的 OpenAI 兼容服务器，设 `compat.supportsDeveloperRole: false` / `compat.supportsReasoningEffort: false`。

## 当前 Pi 行为

- 认证来源优先级：`/login`（auth.json）、环境变量、CLI `--api-key`。
- 订阅 Provider：Claude Pro/Max、ChatGPT Plus/Pro（Codex）、GitHub Copilot、OpenRouter。
- API Key Provider：Anthropic、OpenAI、Google、DeepSeek、Mistral、Groq、Kimi、MiniMax、Xiaomi MiMo 等。
- 自定义 Provider 当前入口：扩展里 `pi.registerProvider(...)` 配 pi-ai 的 `createProvider` 与 `api`（如 `openAICompletionsApi()`）；`streamSimple` 已移到 `@earendil-works/pi-ai/compat`，是兼容导出。
- `models.json` 里未配置认证的模型会加载但不出现在 `/model`，直到有可用认证。

## 在 Pi 里怎么操作

- `/login`：选择并登录 Provider（订阅 OAuth 或写入 API Key 到 `~/.pi/agent/auth.json`）。
- `/model`：打开模型选择器；切换模型后重新检查上下文窗口与工具支持。
- `/logout`：清除已存凭据。
- 自定义 Provider/模型写入 `~/.pi/agent/models.json`。
- 环境变量方式：如 `export ANTHROPIC_API_KEY=...` 后启动 pi；凭据不要写进版本库。

## Python 对照

[provider_registry.py](../../learn_pi_lab/labs/provider_registry.py) 只保存非敏感元数据（不读环境变量、不调用 Provider），拒绝重复模型，提供稳定排序目录：

```python
registry = ProviderRegistry()
registry.register("openai-completions", "demo-1", "Demo Model", 128_000)
selection = registry.select("openai-completions", "demo-1")
# catalog() 按 (provider_id, model_id) 排序返回不可变目录
```

教学点：注册表把"标识合法性、重复检测、排序目录"做成一件事，与 Pi 的 `model-registry.ts` 职责同构。`_validate_identifier` 用正则约束 provider/model id（小写字母、数字、`. _ -`），防止用不可靠的标识做 key。

Tau 对照：`tau_coding/provider_catalog.py`（内置目录）、`tau_coding/provider_config.py`（配置解析）与 `tau_ai/provider.py`（Provider 协议）。

## 实现对照：Pi 源码与 Tau 双版本

Provider 层两套实现的分工一致：目录/注册表管“有哪些模型”，配置解析管“怎么调用”。

**注册（Pi）与目录（Tau）**：

```typescript
// Pi 0.84.2: packages/coding-agent/src/core/model-registry.ts（原文节选）
registerProvider(provider: Provider): void;
registerProvider(providerName: string, config: ProviderConfigInput): void;
registerProvider(providerOrName: Provider | string, config?: ProviderConfigInput): void {
  // 完整 Provider 对象，或 provider 名 + 配置 两种形态
}
unregisterProvider(providerName: string): void { ... }
```

```python
# Tau: tau_coding/provider_catalog.py（原文节选）
class ProviderCatalogEntry:
    """Provider 目录中的单条元数据。"""
    # ...provider / models / 认证来源等字段

BUILTIN_PROVIDER_CATALOG: tuple[ProviderCatalogEntry, ...] = _load_builtin_catalog()

def builtin_provider_entry(name: str) -> ProviderCatalogEntry | None:
    """按名称返回内置目录条目。"""
```

概念对照：Pi 的 `registerProvider` 是**运行时注册**（扩展可增减）；Tau 的 `BUILTIN_PROVIDER_CATALOG` 是**内置目录**（编译期/导入期加载）。两者回答同一个问题：运行时从哪里知道有哪些 Provider、各自的元数据是什么。

**模型元数据**——两套都坚持“元数据是数据，不是代码”：

```python
# Tau: tau_coding/provider_catalog.py（原文节选）
class ModelCostTier:
    """模型成本档位，用于 token 计费。"""

class ModelCatalogMetadata:
    """单个模型的目录元数据。"""
    # context_window / reasoning / cost 等独立维度

def model_cost_for_input_tokens(...): ...
```

对应 Pi 的 models.json 模型字段（`contextWindow`、`reasoning`、`cost`）——再次印证本章开头的判断：上下文窗口、推理能力、成本是相互独立的元数据维度。

## Python 实验

```sh
python3 -m learn_pi_lab lab providers   # 打印非敏感模型目录
```

## 验证方式

```sh
python3 -m unittest tests.test_08_provider_registry -v
```

## 边界与安全

- 凭据从来不应写进课程示例、日志或版本库；为每个 Provider 使用最小范围凭据。
- 区分个人与项目配置；模型显示名/上下文窗口/API 类型不能互相推断。
- 本课程注册表不解释 Pi 的 models.json，生产配置以固定基线文档为准。
- 本地模型（Ollama 等）的 key 是占位符，不代表真实认证；按需用 `/login` 或 `--api-key` 提供。
