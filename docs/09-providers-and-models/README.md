# Provider 与模型配置

模型选择包含认证、Provider API 类型、模型元数据和工作区策略。凭据从来不应写进课程示例、日志或版本库。

## 当前 Pi 行为

Pi 的模型配置位于 models.json；其中 providers 是以 Provider 标识为键的对象映射，不是列表。Provider API 名称包含 openai-completions。认证来源、优先级和可用模型以固定基线的 models、settings 和 custom-provider 文档为准。

自定义 Provider 的当前适配入口是 `pi.registerProvider()`，配 pi-ai 的 `createProvider` 与 `api`（如 `openAICompletionsApi()`）；`streamSimple` 已移到 `@earendil-works/pi-ai/compat`，属于兼容导出。模型显示名、上下文窗口和 API 类型是不同维度，不能仅按模型字符串推断权限或费用。

## Python 对照实验

[provider_registry.py](../../learn_pi_lab/labs/provider_registry.py) 只保存非敏感元数据，拒绝重复模型，并提供稳定排序目录：

    python3 -m unittest tests.test_08_provider_registry -v

该注册表没有读取环境变量、不会调用 Provider，也不解释 Pi 的 models.json。

## 配置建议

为每个 Provider 使用最小范围的凭据，区分个人与项目配置，并在切换模型后重新检查上下文窗口、工具支持与成本策略。
