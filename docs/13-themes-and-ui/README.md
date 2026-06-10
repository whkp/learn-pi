# 主题与 UI 定制

> 通过主题和 UI 扩展，打造个性化的 Pi 界面。

---

## 一、主题系统

### 1.1 内置主题

| 主题 | 说明 |
|------|------|
| `dark` | 深色主题（默认） |
| `light` | 浅色主题 |

### 1.2 切换主题

```
/settings
```

或在 `settings.json` 中：

```json
{
  "theme": "light"
}
```

### 1.3 主题热重载

修改主题文件后，Pi 会立即应用更改，无需重启。

---

## 二、自定义主题

### 2.1 主题位置

| 位置 | 作用域 |
|------|--------|
| `~/.pi/agent/themes/` | 全局 |
| `.pi/themes/` | 项目级 |
| `themes/` 目录（包内） | 包内 |

### 2.2 主题结构

主题是 JSON 文件，定义颜色方案：

```json
{
  "name": "my-theme",
  "colors": {
    "background": "#1e1e1e",
    "foreground": "#d4d4d4",
    "primary": "#569cd6",
    "secondary": "#4ec9b0",
    "accent": "#c586c0",
    "error": "#f44747",
    "warning": "#cca700",
    "success": "#6a9955",
    "info": "#569cd6"
  },
  "editor": {
    "border": "#3c3c3c",
    "borderFocused": "#569cd6",
    "placeholder": "#808080"
  },
  "message": {
    "user": "#d4d4d4",
    "assistant": "#d4d4d4",
    "tool": "#808080",
    "system": "#569cd6"
  }
}
```

### 2.3 加载自定义主题

```bash
pi --theme ./my-theme.json
```

或在 `settings.json` 中：

```json
{
  "themes": ["./my-theme.json"]
}
```

---

## 三、UI 扩展

### 3.1 通知

```typescript
// 信息通知
ctx.ui.notify("操作完成", "info");

// 错误通知
ctx.ui.notify("操作失败", "error");

// 警告通知
ctx.ui.notify("请检查", "warning");
```

### 3.2 状态栏

```typescript
// 设置状态
ctx.ui.setStatus("my-ext", "处理中...");

// 清除状态
ctx.ui.setStatus("my-ext", null);
```

### 3.3 Widget

在编辑器上方或下方显示内容：

```typescript
// 默认在编辑器上方
ctx.ui.setWidget("my-ext", [
  "当前分支: main",
  "未提交更改: 3",
  "测试通过: ✓"
]);

// 指定位置
ctx.ui.setWidget("my-ext", lines, "above");  // 编辑器上方
ctx.ui.setWidget("my-ext", lines, "below");  // 编辑器下方

// 清除
ctx.ui.setWidget("my-ext", null);
```

### 3.4 Footer

```typescript
// 自定义 Footer
ctx.ui.setFooter([
  "分支: main",
  "Token: 1234",
  "费用: $0.05"
]);

// 清除
ctx.ui.setFooter(null);
```

### 3.5 Header

```typescript
// 自定义 Header
ctx.ui.setHeader([
  "Pi 编码智能体 v1.0"
]);

// 清除
ctx.ui.setHeader(null);
```

### 3.6 自定义编辑器

```typescript
// 替换编辑器组件
ctx.ui.setEditorComponent(myCustomEditor);

// 设置编辑器文本
ctx.ui.setEditorText("新的内容");

// 获取编辑器文本
const text = ctx.ui.getEditorText();
```

---

## 四、对话框

### 4.1 选择列表

```typescript
const choice = await ctx.ui.select("选择环境", [
  { label: "Staging", value: "staging" },
  { label: "Production", value: "production" }
]);

if (choice) {
  ctx.ui.notify(`选择了: ${choice}`, "info");
}
```

### 4.2 确认对话框

```typescript
const ok = await ctx.ui.confirm("确认删除", "确定要删除这个文件吗？");

if (ok) {
  // 执行删除
}
```

### 4.3 输入对话框

```typescript
const input = await ctx.ui.input("输入版本号", "1.0.0");

if (input) {
  ctx.ui.notify(`版本号: ${input}`, "info");
}
```

### 4.4 带超时的对话框

```typescript
const controller = new AbortController();
setTimeout(() => controller.abort(), 5000);  // 5秒超时

const ok = await ctx.ui.confirm("确认", "继续？", controller.signal);
```

---

## 五、思考块显示

### 5.1 折叠/展开

- **Ctrl+T**：折叠/展开思考块

### 5.2 隐藏思考标签

```typescript
ctx.ui.setHiddenThinkingLabel("思考中...");
```

### 5.3 工作指示器

```typescript
ctx.ui.setWorkingIndicator("思考中...");
```

---

## 六、消息渲染

### 6.1 自定义渲染

通过扩展注册自定义消息渲染器：

```typescript
pi.registerMessageRenderer({
  toolName: "my-tool",
  render: (message) => {
    return [
      { type: "text", text: `工具: ${message.toolName}` },
      { type: "text", text: `结果: ${message.content}` }
    ];
  }
});
```

### 6.2 折叠工具输出

- **Ctrl+O**：折叠/展开工具输出

---

## 七、完整示例：状态监控扩展

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  let turnCount = 0;
  
  // 每次回合结束更新状态
  pi.on("turn_end", async (event, ctx) => {
    turnCount++;
    
    // 更新 Widget
    ctx.ui.setWidget("status-monitor", [
      `已完成 ${turnCount} 个回合`,
      `当前模型: ${event.model}`,
      `Token 用量: ${event.usage.totalTokens}`
    ]);
    
    // 更新 Footer
    ctx.ui.setFooter([
      `回合: ${turnCount}`,
      `Token: ${event.usage.totalTokens}`,
      `费用: $${event.usage.cost.toFixed(4)}`
    ]);
  });
  
  // 会话开始时初始化
  pi.on("session_start", async (event, ctx) => {
    turnCount = 0;
    ctx.ui.notify("状态监控已启动", "info");
  });
}
```

---

## 八、小结

| 功能 | 说明 |
|------|------|
| **内置主题** | dark、light |
| **自定义主题** | JSON 文件定义颜色 |
| **热重载** | 修改立即生效 |
| **Widget** | 编辑器上下方显示内容 |
| **Footer/Header** | 自定义底部/顶部 |
| **对话框** | 选择、确认、输入 |
| **消息渲染** | 自定义工具输出显示 |

---

## 下一步

掌握了主题和 UI 定制后，下一章我们将介绍 [常用扩展实战](../14-common-extensions/README.md)，学习如何实现联网搜索、计划模式等实用功能。
