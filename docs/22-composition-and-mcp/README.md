# 组合、资源与 MCP 边界

将技能、扩展、资源和外部协议组合起来时，接口边界比“能连上”更重要。

## 学习目标

- 用稳定的数据模型发现课程资源。
- 了解 JSONL 逐帧解析的基本约束。
- 明确 MCP 或任意外部工具协议都需要独立的信任和授权边界。

## 当前 Pi 行为

Pi 支持技能、扩展和 RPC 等组合点。技能发现的目录规则、扩展 API 与 RPC 帧的生产格式会随 Pi 版本演进，必须查阅固定基线的 skills、extensions、rpc 和 json 文档。课程 JSONL 解析器不是 Pi RPC 的完整协议实现，也不实现 MCP 客户端。

## Python 实验

resources.py 递归扫描课程自己的 LESSON.md 资源，拒绝符号链接和重复名称。rpc_jsonl.py 把不完整字节流缓冲到换行符，再验证 id、method 与 params：

    from learn_pi_lab.labs.rpc_jsonl import JsonlRpcCodec

    codec = JsonlRpcCodec()
    messages = codec.feed('{"id":"1","method":"ping","params":{}}\n')
    print(messages[0].method)

## 验证方式

    python3 -m unittest tests.test_06_resources tests.test_10_rpc_jsonl -v

## 边界与安全

不要把远端技能描述、工具注释或协议载荷当作可信指令。对每个服务器单独配置权限、最大消息大小、超时、凭据范围和可调用的方法集合。
