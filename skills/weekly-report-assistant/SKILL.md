---
name: weekly-report-assistant
description: Use when the user asks to fill, update, or append weekly reports (周报) on a SeaTable-based system, or when analyzing git commits to generate weekly progress summaries. Triggers include "周报", "weekly report", "fill report", "append progress".
---

# Weekly Report Assistant

Automates weekly report operations on SeaTable-based report systems using `playwright-cli`. Analyzes recent activity (via GitLab API or local git commits) to generate structured progress summaries, then navigates the web UI to fill or append content with correct rich-text formatting.

**REQUIRED TOOL:** `playwright-cli` must be installed (`npm install -g @playwright/cli`).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WEEKLY_REPORT_URL` | Yes | 周报系统页面的完整 URL（不是 SeaTable 首页） |

**First-time setup:** If `WEEKLY_REPORT_URL` is not set, instruct the user to configure it permanently.

URL 必须精确指向**周报系统**页面，而不是 SeaTable 首页或其他表。获取方式：在浏览器中打开周报系统，看到"周报填写"/"我的周报"等视图后，复制地址栏的完整 URL。通常格式为 `https://<host>/external-apps/<uuid>/`。

```bash
# Fish shell
set -Ux WEEKLY_REPORT_URL "https://inner-table.example.com/external-apps/<uuid>/"

# Bash/Zsh — add to ~/.bashrc or ~/.zshrc
export WEEKLY_REPORT_URL="https://inner-table.example.com/external-apps/<uuid>/"
```

Do not proceed until the variable is set.

## Quick Reference

| Task | Reference |
|------|-----------|
| Activity analysis & content generation | [references/git-analysis.md](references/git-analysis.md) |
| SeaTable Slate editor operations | [references/slate-editor.md](references/slate-editor.md) |
| Navigation & authentication | [references/navigation.md](references/navigation.md) |

## Workflow

1. **Analyze recent activity** for the target week → see [git-analysis.md](references/git-analysis.md)
2. **Deduplicate** against previous week's report content
3. **Navigate and authenticate** via `playwright-cli` → see [navigation.md](references/navigation.md)
4. **Locate** the target record in the report list
5. **Edit** using Slate-compatible operations → see [slate-editor.md](references/slate-editor.md)
6. **Verify** content structure before closing

## Report Content Format

SeaTable rich text uses this structure:

```
H3: Project/Component Name
UL:
  - Completed task 1
  - Completed task 2

H3: Another Component
UL:
  - Task 3
  - Task 4
```

Keep items concise (one line each). Group by project, not by date.
