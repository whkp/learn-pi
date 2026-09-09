# Provider 与模型 —— 一行代码驾驭多个模型

> Agent 需要同时面对多家 LLM：认证方式不同、API 格式不同、模型元数据不同。Provider 层的核心设计是**三者分离**：元数据（有哪些模型）、协议（怎么调用）、认证（凭什么授权）互相独立——因此"不能仅按模型字符串推断权限或费用"。

## 学习目标

- 理解 Provider 注册表如何组织"认证 + API 类型 + 模型元数据"。
- 看懂 models.json 的结构：providers 是对象映射、api 决定协议。
- 理解两种注册形态：完整 Provider vs 名 + 配置。

## 一、问题：接一家模型是配置，接十家就是架构

只用一个模型，写死调用代码就够了。但 Agent 要面对：Claude 的订阅、OpenAI 的 API key、本机 Ollama、公司的内网网关……每一家的认证方式、请求格式、模型清单都不一样。

如果每接一家就改一遍调用代码，代码会迅速腐化。Provider 层的存在，就是把这堆差异**收敛成一个统一接口**。

## 二、三者分离：元数据、协议、认证

| 维度 | 回答的问题 | 例子 |
|------|-----------|------|
| 元数据 | 有哪些模型 | id、显示名、contextWindow、reasoning、cost |
| API 类型 | 怎么调用 | openai-completions、anthropic-messages、google-generative-ai |
| 认证 | 凭什么授权 | 订阅 OAuth、API key、环境变量 |

三者分离的意义：

- **`/model` 只读元数据**：模型选择器不关心认证，只列可用模型。
- **调用走统一流式接口**：`stream_response(model, system, messages, tools)`——不管背后是哪个 Provider。
- **认证独立解析**：`/login` 的 auth.json、环境变量、`--api-key` 是三条独立来源。

`contextWindow`、`reasoning`、`cost` 是相互独立的维度——显示名相近的模型，能力可能完全不同。所以"模型字符串"不能用来推断权限或费用。

## 三、两种注册形态

扩展注册 Provider 有两种方式，按需选择：

- **完整 Provider 对象**：自定义认证、过滤、刷新、流式行为——深度定制时用。
- **provider 名 + 配置**：只覆盖 baseUrl / apiKey / api / models——对接 OpenAI 兼容服务器等常见场景。

## 四、models.json：providers 是映射不是列表

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

三个要点：

1. **`providers` 是以标识为键的对象映射，不是列表**——这是课程反复强调的事实点。
2. **`api` 决定协议**，可设在 provider 层（默认）或 model 层（覆盖）。
3. **`apiKey` 可以是占位符**：本地服务器（Ollama）忽略 key，但 pi 仍按"需要认证"处理模型，所以占位 + `/login` 存 key，或 `--api-key` 传入。

对不支持 `developer` role 的 OpenAI 兼容服务器，用 `compat.supportsDeveloperRole: false` 降级。

## 当前 Pi 行为

- 订阅 Provider：Claude Pro/Max、ChatGPT Plus/Pro（Codex）、GitHub Copilot、OpenRouter；API Key Provider：Anthropic、OpenAI、Google、DeepSeek、Mistral、Groq、Kimi、MiniMax、小米 MiMo 等。
- 自定义 Provider 当前入口：`pi.registerProvider(...)` 配 pi-ai 的 `createProvider` 与 `api`（如 `openAICompletionsApi()`）；`streamSimple` 已移到 compat 包，是兼容导出。
- 未配置认证的模型会加载但不出现 `/model`，直到有可用认证。
- 0.85.1 新增 GPT-6 Astra（OpenAI API Key 与 Codex 订阅均可用）；0.85.0 起支持的 Anthropic 传输会按轮次保留 thinking effort，并在签名不匹配时安全恢复。
- 模型目录是纯数据：`ModelRuntime.create()` 列出可用模型，挑不出可用模型就抛错——「有没有模型」在启动时就是可判定的，不需要等第一次请求失败。

### 源码证据表

| 教学结论 | Pi 路径 / 符号 | 说明 |
|---|---|---|
| 自定义 Provider 入口 | `pi.registerProvider()` | 配 `createProvider` + `api` |
| 兼容导出非首选 | `@earendil-works/pi-ai/compat` `streamSimple` | 保留但不推荐 |
| 模型注册表 | `packages/coding-agent/src/core/model-registry.ts` | 元数据与认证分离 |
| 协议适配 | `packages/coding-agent/docs/custom-provider.md` | 协议翻译层说明 |
| 模型配置文档 | `packages/coding-agent/docs/models.md` | 0.85 起含 thinking effort 持久化 |

## 失败与边界实验

Provider 层的失败集中在「三件事被混在一起」的时候：

1. **认证缺失被当成模型不存在。** 修复前：没有 Key 的模型从列表消失，用户以为不支持；修复后（当前行为）：模型加载但 `/model` 不出现，配上认证即出现。区别在于**状态可解释**——「加载了但没凭据」比「不存在」可诊断得多。
2. **协议差异写进业务代码。** 在循环里 `if provider == "anthropic": ...` 会让每个新 Provider 都改循环。修法：协议差异收敛在 translator 层，循环只面向统一消息类型。
3. **thinking 签名不匹配。** Anthropic 的签名思考块在重放/传输中可能失配。0.85.0 起的做法是按轮次保留 effort 并安全恢复，而不是丢弃整个思考块——降级而不是失败。

```sh
python3 -m learn_pi_lab lab providers
python3 -m unittest tests.test_08_provider_registry -v
```

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

> 这一模块的核心代码在[核心代码导览 · Provider 注册表](../code-tour.md)有逐段解读。

## 验证方式

```sh
python3 -m unittest tests.test_08_provider_registry -v
```

## 边界与安全

- 凭据从来不应写进课程示例、日志或版本库；为每个 Provider 使用最小范围凭据。
- 模型显示名/上下文窗口/API 类型不能互相推断；本地模型（Ollama）的 key 是占位符，不代表真实认证。

## 回顾

- **三者分离**：元数据、协议、认证独立——模型字符串不能推断权限。
- **models.json**：providers 是映射不是列表；api 决定协议；apiKey 可为占位符。
- **两种注册形态**：完整 Provider vs 名 + 配置。

模型调用会失败——网络抖动、限流、配额耗尽。下一章[可靠性](../09-reliability/README.md)讲失败如何重试与隔离。
