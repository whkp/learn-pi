<div class="home-hero">
  <h1>Learn Pi</h1>
  <p class="tagline">面向开发者的 Pi 编码智能体学习仓库：准确资料、可运行的 Python 实验、自动化测试与离线实战项目。</p>
  <div class="hero-actions">
    <a class="hero-btn primary" href="01-architecture/">从架构开始读</a>
    <a class="hero-btn secondary" href="02-agent-loop/">直接看 Agent Loop</a>
  </div>
</div>

## 这门课在讲什么

**agent = LLM + tool use**。模型提供语言、推理，以及"下一步调用哪个工具"的决策；其余一切——消息、工具、权限、上下文、会话——都由包住模型的 harness 提供。本课程以 Pi 为蓝本，每一章围绕一个大主题，讲清"是什么 / 怎么做 / 为什么"，重点介绍 Pi 的核心设计。

- **固定基线**：Pi 0.84.2 @ `914cf1472e715297caa30db4b9535d534a9eb718`，任何 API 细节以该版本源码和官方文档（pi.dev）为准。
- **双重对照**：每章配有可运行的 Python 教学模型（标准库、离线、确定），以及 Tau（Pi 的 Python 对照实现）的真实代码。
- **工程化验证**：107 个单元测试 + 课程契约检查 + 链接检查，全部离线可复现。

## 章节总览

<!-- course-chapter-manifest:start -->
- `00-course-map.md`
- `01-architecture/README.md`
- `02-agent-loop/README.md`
- `03-tools/README.md`
- `04-messages-and-memory/README.md`
- `05-sessions/README.md`
- `06-events-and-extensions/README.md`
- `07-context-and-compaction/README.md`
- `08-providers-and-models/README.md`
- `09-reliability/README.md`
- `10-protocol-and-integration/README.md`
- `11-projects-and-evaluation/README.md`
<!-- course-chapter-manifest:end -->

<div class="chapter-grid">
  <a class="chapter-card" href="01-architecture/">
    <span class="card-num">01</span>
    <h3>架构总览</h3>
    <p>Pi 的分层与核心设计：agent = LLM + tool use，模型无关的核心、产品环境、前端如何通过事件契约解耦。</p>
  </a>
  <a class="chapter-card" href="02-agent-loop/">
    <span class="card-num">02</span>
    <h3>Agent Loop</h3>
    <p>循环如何驱动模型工作：模型决定、harness 执行；Trace 与 Turn 的区别；stopReason 是唯一终止信号。</p>
  </a>
  <a class="chapter-card" href="03-tools/">
    <span class="card-num">03</span>
    <h3>工具系统</h3>
    <p>工具如何被声明、注册与约束：schema + executor、注册表分发、软约束与硬闸门、bash 特权工具。</p>
  </a>
  <a class="chapter-card" href="04-messages-and-memory/">
    <span class="card-num">04</span>
    <h3>消息与记忆</h3>
    <p>对话历史如何组织与传递：role 判别、工具成对回填、两类记忆的分工。</p>
  </a>
  <a class="chapter-card" href="05-sessions/">
    <span class="card-num">05</span>
    <h3>会话管理</h3>
    <p>对话如何存储、恢复与分叉：JSONL v3、append-only 的树、认父不认子、分支是回退的自然结果。</p>
  </a>
  <a class="chapter-card" href="06-events-and-extensions/">
    <span class="card-num">06</span>
    <h3>事件驱动与扩展</h3>
    <p>事件即契约：两条监听通道的分水岭、扩展如何按需注入能力、社区扩展生态。</p>
  </a>
  <a class="chapter-card" href="07-context-and-compaction/">
    <span class="card-num">07</span>
    <h3>上下文压缩</h3>
    <p>有限窗口如何装下无限对话：两层防护、压缩不是丢消息而是让模型总结它自己、成对不拆。</p>
  </a>
  <a class="chapter-card" href="08-providers-and-models/">
    <span class="card-num">08</span>
    <h3>Provider 与模型</h3>
    <p>一行代码驾驭多个模型：元数据、协议、认证三者分离，models.json 的结构。</p>
  </a>
  <a class="chapter-card" href="09-reliability/">
    <span class="card-num">09</span>
    <h3>可靠性</h3>
    <p>失败如何重试与隔离：先分类再重试、指数退避必封顶、错误信息脱敏。</p>
  </a>
  <a class="chapter-card" href="10-protocol-and-integration/">
    <span class="card-num">10</span>
    <h3>协议与集成</h3>
    <p>SDK、RPC 与 JSONL 边界：stdout 是协议、增量分帧处理粘包/半包、方法白名单。</p>
  </a>
  <a class="chapter-card" href="11-projects-and-evaluation/">
    <span class="card-num">11</span>
    <h3>实战与评测</h3>
    <p>四个离线 mini-project 训练可迁移的 Agent 工程边界，测试与评测构成同一条质量链。</p>
  </a>
  <a class="chapter-card" href="glossary.md">
    <span class="card-num">附</span>
    <h3>术语表</h3>
    <p>课程涉及的关键术语：Pi 基线、当前 Pi 行为、Python 教学模型、主章节。</p>
  </a>
</div>

## 学习目标

- 了解课程以哪个 Pi 版本为准，以及如何查找相应的源码说明。
- 区分 Pi 的 TypeScript 实现、Tau 的 Python 实现与本课程的离线 Python 教学模型。
- 使用本仓库的检查脚本验证课程资料。

## 当前 Pi 行为

Pi 的实际行为以固定版本（0.84.2）的源码为准；课程叙述应链接到 [Pi 源码映射](pi-source-map.md)，而不是把示例 Python 当作 Pi 的生产实现。

## Python 实验

课程实验位于 `learn_pi_lab` 包中，且只依赖 Python 标准库。可以先运行：

```sh
python3 -m learn_pi_lab
```

## 配套资料

- [Pi 源码映射](pi-source-map.md) —— 固定基线、源码入口、已校正的易错点
- [术语表](glossary.md) —— 关键术语定义
- [Tau](https://github.com/huggingface/tau) —— Pi 的 Python 对照实现（tau_agent / tau_ai / tau_coding）

## 验证方式

在仓库根目录运行以下命令：

```sh
python3 scripts/check_course_contract.py
python3 scripts/check_markdown_links.py
```

两条命令成功时都会输出 `OK`。

## 边界与安全

- 本课程 Python 教学模型只依赖标准库：不访问网络、不调用模型、不执行学习者提供的 shell 命令。
- 教学模型 ≠ 生产实现：示例中的固定数据和策略不可直接替代生产配置。
- 迁移到 Pi 时用 TypeScript 重新实现，并补齐认证、权限、取消、日志脱敏与端到端测试。
