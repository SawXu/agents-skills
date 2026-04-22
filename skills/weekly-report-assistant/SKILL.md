---
name: weekly-report-assistant
description: Use when the user asks to fill, update, or append weekly reports (周报) on a SeaTable-based system, or when analyzing git commits to generate weekly progress summaries. Applies when SeaTable rich-text fields must be edited safely, especially when `opencli-browser` navigation is acceptable but Slate editor persistence is fragile.
---

# Weekly Report Assistant

Automates weekly report operations on SeaTable-based report systems. It analyzes recent activity (via GitLab API or local git commits), generates structured progress summaries, and fills the SeaTable UI with Slate-safe rich-text operations.

**Preferred tool:** `playwright-cli` for any Slate rich-text create/replace flow.

**Allowed tool split:**

- Use `opencli-browser` for page navigation, view switching, locating the target row, and post-submit verification.
- Use `playwright-cli` for SeaTable Slate editor replacement, append, and any edit that must persist reliably.
- If the user explicitly requires `opencli-browser` for submission, only use it with the proven paste-like path from `references/slate-editor.md`. Do **not** rely on `opencli browser type` for SeaTable rich-text persistence.

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
3. **Navigate and authenticate** via `playwright-cli` or `opencli-browser` → see [navigation.md](references/navigation.md)
4. **Locate** the target record in the report list
5. **Edit** using Slate-compatible operations → see [slate-editor.md](references/slate-editor.md)
6. **Verify** content structure before closing

## Tool Decision Rules

- `playwright-cli`: default for create, replace, append, or cleanup inside SeaTable Slate rich-text fields.
- `opencli-browser`: good for opening the system, switching between `周报填写` and `我的周报`, selecting `填写人`, finding the current week's row, and checking whether a record exists.
- `opencli-browser` plus custom page-side paste event: acceptable for creating a **new** weekly report when the field is still empty and you verify the form preview changed from `编辑文本` to rendered paragraphs.
- `opencli-browser` plus default `type`: not acceptable for SeaTable Slate fields. It can show text inside the popup editor while the underlying form field still remains empty.
- Editing an **existing** rich-text cell in `我的周报` with `opencli-browser` is high risk. The editor may keep stale nodes and partially merge old/new content. Prefer `playwright-cli`.

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
