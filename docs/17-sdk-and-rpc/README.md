# SDK 与 RPC 编程接口

SDK 和 RPC 适合把 Pi 接入自己的宿主程序，但它们不是绕开权限、认证和会话管理的捷径。

## 当前 Pi 行为

SDK 订阅事件使用 session.subscribe，而不是 session.on。创建 coding tools 时必须提供 cwd，例如工作目录；createCodingTools 需要该边界来构造文件与命令相关工具。RPC 和 JSON 模式的启动参数、帧类型与输出顺序以固定基线的 sdk、rpc 和 json 文档为准。

JSONL 是按换行分帧的格式。消费者必须处理粘包、半包、无效 JSON 和未知事件，不能假设一次读取恰好对应一个对象。

## Python 对照实验

[rpc_jsonl.py](../../learn_pi_lab/labs/rpc_jsonl.py) 只解析课程定义的 id、method、params 请求，并限制未终止缓冲区大小：

    python3 -m unittest tests.test_10_rpc_jsonl -v

[rpc_console.py](../../projects/rpc_console.py) 只支持 ping，返回 JSON，不创建子进程。

## 安全提示

生产集成应将 stdout 保留给协议数据，把诊断写到 stderr，并限制可调用方法、消息大小、超时和凭据范围。不要把 RPC 参数拼接成 shell 命令。
