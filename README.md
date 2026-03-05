# Agents Skills

SawXu 的 AI 编码助手技能集


## 安装

```bash
npx skills add SawXu/agents-skills
```

[`skills`](https://www.npmjs.com/package/skills) CLI 会自动检测已安装的 AI 代理并提供交互式选择。使用 `-g` 全局安装，或 `-y` 安装所有技能。

支持 Claude Code、Cursor、Codex、OpenCode、GitHub Copilot、Antigravity、Roo Code 等。

### Claude Code Marketplace

Claude Code 用户也可通过 Marketplace 安装：

```bash
# 添加 marketplace
/plugin marketplace add SawXu/agents-skills

# 安装单个技能
/plugin install <skill-name>@agents-skills
```

### 手动安装

克隆仓库并将技能文件夹复制到对应代理的目录：

| 代理        | 项目级路径         | 全局路径                    |
| ----------- | ------------------ | --------------------------- |
| Claude Code | `.claude/skills/`  | `~/.claude/skills/`         |
| Cursor      | `.cursor/skills/`  | `~/.cursor/skills/`         |
| Codex       | `.codex/skills/`   | `~/.codex/skills/`          |
| OpenCode    | `.opencode/skill/` | `~/.config/opencode/skill/` |
| Copilot     | `.github/skills/`  | —                           |

## 技能列表

| 技能 | 说明 |
| ---- | ---- |
| `weekly-report-assistant` | 自动化周报填写：分析 git 提交生成结构化摘要，通过浏览器自动化填写 SeaTable 周报系统 |

## 技能工作原理

技能遵循 [Agent Skills](https://agentskills.io) 开放格式，有两种激活方式：

1. **自动发现** — 代理读取每个技能的 `description`，在与当前任务相关时自动加载
2. **手动调用** — 输入 `/skill-name`（如 `/my-skill`）显式加载技能

## 仓库结构

遵循 [agentskills](https://github.com/agentskills/agentskills) 标准格式。

```
agents-skills/
├── skills/                 # 技能目录（agentskills 格式）
│   └── <skill-name>/
│       ├── SKILL.md        # 入口文件（含 frontmatter）
│       └── references/     # 按需加载的参考文档
└── .claude-plugin/
    └── marketplace.json    # Claude Code Marketplace 清单
```

### SKILL.md 格式

每个技能入口使用 YAML frontmatter：

```yaml
---
name: skill-name
description: 何时使用此技能 — 触发条件和使用场景
license: MIT
---

# 技能标题

简要概述及指向 references 子文件的快速参考表。
```

### 渐进式加载

技能采用渐进式加载 — 主 `SKILL.md` 保持精简（约 300 tokens），通过 `references/` 子文件按需加载详细内容，最大限度减少上下文占用。

## 参考资料

- [Agent Skills 规范](https://agentskills.io) - AI 代理能力扩展的开放格式
- [Claude Code Skills](https://code.claude.com/docs/en/skills) - Claude Code 中的技能
- [VS Code Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills) - GitHub Copilot 技能
- [GitHub Agent Skills 文档](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) - 关于代理技能

## 许可证

MIT — Copyright (c) 2026 SawXu
