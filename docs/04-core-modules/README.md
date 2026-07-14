# 核心模块源码解读

本章说明阅读源码时应确认的边界，不将教学伪代码伪装成当前 API。

## ai 与 Provider

ai 包提供统一消息与 Provider 适配层。自定义 Provider 的流式实现应使用当前的 streamSimple 接口；Provider 名称和模型数据由 coding-agent 的模型配置消费。具体字段请从固定基线的 models 与 custom-provider 文档、类型定义交叉核对。

## agent 运行时

agent 包维护消息、工具、流式事件和中止等通用机制。订阅生命周期时使用会话提供的 subscribe 接口；不要把不存在的 session.on 当作 SDK API。

## coding-agent

coding-agent 负责工作目录、会话持久化、设置、工具集、扩展和交互界面。创建编码工具时必须传入工作目录；createCodingTools 不是无参数的全局工具工厂。最小化工具集也应从工作目录、允许的操作和用户确认策略开始设计。

## Python 对照实验

[tool_permissions.py](../../learn_pi_lab/labs/tool_permissions.py) 展示了先检查意图和路径、再调用注入执行器的顺序。测试证明被拒绝的请求不会触发执行器：

    python3 -m unittest tests.test_02_tool_permissions -v

这与 Pi 的实际工具实现不等价，只用于解释可测试的边界。
