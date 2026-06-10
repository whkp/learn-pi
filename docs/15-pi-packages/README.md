# Pi Packages 包管理

> 通过 npm 或 git 安装、创建和分享扩展包。

---

## 一、包管理概览

### 1.1 什么是 Pi 包？

Pi 包是可分享的扩展集合，包含：
- **扩展**（Extensions）
- **技能**（Skills）
- **提示词模板**（Prompts）
- **主题**（Themes）

### 1.2 包来源

| 来源 | 说明 |
|------|------|
| npm | 从 npmjs.com 安装 |
| git | 从 Git 仓库安装 |
| 本地 | 从本地路径安装 |

---

## 二、安装包

### 2.1 npm 包

```bash
pi install npm:pi-skills
pi install npm:@foo/bar
pi install npm:@foo/bar@1.2.3  # 指定版本
```

### 2.2 git 包

```bash
pi install git:github.com/user/repo
pi install git:github.com/user/repo@v1  # 标签或 commit
pi install git:git@github.com:user/repo
pi install git:git@github.com:user/repo@v1
pi install https://github.com/user/repo
pi install https://github.com/user/repo@v1
pi install ssh://git@github.com/user/repo
pi install ssh://git@github.com/user/repo@v1
```

### 2.3 项目本地安装

```bash
pi install npm:pi-skills -l
pi install git:github.com/user/repo -l
```

项目本地包安装到 `.pi/npm/` 或 `.pi/git/`。

---

## 三、管理包

### 3.1 列出已安装包

```bash
pi list
```

### 3.2 更新包

```bash
pi update                    # 更新所有包（跳过固定版本）
pi update --extensions       # 只更新包
pi update --self             # 只更新 Pi
pi update --self --force     # 强制重新安装 Pi
pi update npm:@foo/bar       # 更新指定包
```

### 3.3 移除包

```bash
pi remove npm:pi-skills
pi uninstall npm:pi-skills   # 别名
pi remove git:github.com/user/repo
```

### 3.4 配置包

```bash
pi config
```

交互式启用/禁用包的扩展、技能、提示词、主题。

---

## 四、创建包

### 4.1 包结构

```
my-pi-package/
├── package.json
├── extensions/
│   └── my-extension.ts
├── skills/
│   └── my-skill/
│       └── SKILL.md
├── prompts/
│   └── my-prompt.md
└── themes/
    └── my-theme.json
```

### 4.2 package.json

```json
{
  "name": "my-pi-package",
  "version": "1.0.0",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./extensions"],
    "skills": ["./skills"],
    "prompts": ["./prompts"],
    "themes": ["./themes"]
  }
}
```

### 4.3 自动发现

如果没有 `pi` 清单，Pi 会自动发现：
- `extensions/` 目录中的 `.ts` 文件
- `skills/` 目录中的 `SKILL.md`
- `prompts/` 目录中的 `.md` 文件
- `themes/` 目录中的 `.json` 文件

---

## 五、包配置

### 5.1 全局配置

编辑 `~/.pi/agent/settings.json`：

```json
{
  "packages": [
    "pi-skills",
    "@foo/bar"
  ]
}
```

### 5.2 项目配置

编辑 `.pi/settings.json`：

```json
{
  "packages": [
    "pi-skills",
    {
      "source": "@foo/bar",
      "skills": ["my-skill"],
      "extensions": []
    }
  ]
}
```

### 5.3 过滤包资源

```json
{
  "packages": [
    {
      "source": "pi-skills",
      "skills": ["brave-search", "transcribe"],
      "extensions": []
    }
  ]
}
```

---

## 六、安全注意事项

### 6.1 风险说明

- **扩展**：运行在你的系统权限下，可执行任意代码
- **技能**：可指导模型执行任何操作

### 6.2 安全建议

1. **审查源码**：安装前检查包的内容
2. **信任来源**：只安装信任的包
3. **限制权限**：在容器或沙箱中运行
4. **定期更新**：保持包更新

---

## 七、固定版本

### 7.1 固定 git 版本

```bash
pi install git:github.com/user/repo@v1.0.0
pi install git:github.com/user/repo@abc123  # commit hash
```

固定版本的包在 `pi update` 时会被跳过。

### 7.2 更新固定版本

```bash
pi install git:github.com/user/repo@v1.1.0
```

---

## 八、包目录

### 8.1 全局包

- npm 包：`~/.pi/agent/npm/`
- git 包：`~/.pi/agent/git/`

### 8.2 项目本地包

- npm 包：`.pi/npm/`
- git 包：`.pi/git/`

### 8.3 自定义目录

```json
{
  "packages": ["./my-packages"]
}
```

---

## 九、常用包

### 9.1 官方包

| 包名 | 说明 |
|------|------|
| `pi-skills` | 官方技能集合（搜索、转录等） |
| `anthropic-skills` | Anthropic 官方技能 |

### 9.2 社区包

在 [npmjs.com](https://www.npmjs.com/search?q=keywords%3Api-package) 搜索 `pi-package` 关键词。

---

## 十、小结

| 功能 | 命令 |
|------|------|
| 安装包 | `pi install <source>` |
| 列出包 | `pi list` |
| 更新包 | `pi update` |
| 移除包 | `pi remove <source>` |
| 配置包 | `pi config` |
| 项目本地安装 | `pi install <source> -l` |

---

## 下一步

掌握了包管理后，下一章我们将介绍 [会话压缩与上下文管理](../16-compaction/README.md)，学习如何管理长对话的上下文。
