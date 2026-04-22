---
name: weekly-report-assistant
description: Use when the user asks to fill, update, or append weekly reports (周报) on a SeaTable-based system, or when analyzing git commits to generate weekly progress summaries. Applies when a live browser must be driven through the `opencli-adapter-author` skill and SeaTable Slate rich-text fields need strict post-edit verification.
---

# Weekly Report Assistant

Automates weekly report operations on SeaTable-based report systems. It analyzes recent activity (via GitLab API or local git commits), generates structured progress summaries, and fills the SeaTable UI with Slate-aware rich-text operations.

**Required OpenCLI skill:** `opencli-adapter-author`

**Browser operation rules:**

- Use the `opencli-adapter-author` skill as the top-level workflow for this report system. It provides the recon, adapter, and verify discipline, while the concrete page operations still use `opencli browser *` commands.
- Follow the `opencli-adapter-author` workflow when operating this system: validate the environment with `opencli doctor`, prefer repeatable OpenCLI flows, and use fresh `state` or `find` snapshots before page interactions.
- Treat SeaTable Slate rich-text fields as fragile. Any write must be verified after the popup closes; visible text inside the editor popup alone is not enough.
- When modifying an existing weekly report in `我的周报`, prefer reading the current text, composing the final full content offline, and writing it back through the Slate-compatible paste path. Incremental `type`-based append is not reliable enough.
- If the OpenCLI flow cannot prove the field value persisted, do **not** submit. Stop and ask the user whether to retry or switch to a manual fallback.

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
3. **Navigate and authenticate** under the `opencli-adapter-author` workflow → see [navigation.md](references/navigation.md)
4. **Locate** the target record or open the new-report form
5. **Edit** using the Slate-safe OpenCLI path → see [slate-editor.md](references/slate-editor.md)
6. **Verify** the rendered field value before submit
7. **Submit and re-check** the created or updated record

## Tool Decision Rules

- `opencli-adapter-author` is the required parent skill for this workflow, and the concrete browser operations are executed with `opencli browser *` commands.
- Use `opencli browser state` or `opencli browser find` before each interaction; refs are only valid for the current snapshot.
- Prefer creating the current week's report in `周报填写` when the row does not exist yet.
- Opening an existing `我的周报` long-text cell may require a page-side `dblclick` dispatch. A normal single click on the table cell often only focuses the row and does not open the editor.
- Editing an **existing** rich-text cell in `我的周报` is higher risk than filling a blank field. Re-open and verify the rendered value after each edit.
- Do not rely on popup-only evidence. If the form preview or table cell does not reflect the new content, the write did not persist.

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
