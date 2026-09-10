---
name: weekly-report-assistant
description: Use when the user asks to read, summarize, fill, update, or append weekly/monthly reports (周报/月报), aggregate a month's SeaTable reports, or fill a Xinrenxinshi (薪人薪事) KPI/performance form from report content. Prefer the SeaTable API for reads and use OpenCLI browser automation for verified writes.
license: MIT
---

# Weekly & Monthly Report Assistant

Automates weekly and monthly report operations. It reads SeaTable records through the API, aggregates weekly entries into monthly summaries, analyzes GitLab or local git activity, writes SeaTable Slate fields, and can populate Xinrenxinshi KPI drafts from the resulting report.

**Required OpenCLI skill for browser operations:** `opencli-browser`

**API-first rule:** Read the report records through the private SeaTable API before opening the browser. Follow [references/sea-table-api.md](references/sea-table-api.md) to resolve the external app and discover its tables, views, and columns. Do not put API tokens in skill files, shell history, logs, or report output.

**Browser operation rules:**

- Load `opencli-browser`, validate the bridge with `opencli doctor`, and use a stable named browser session.
- Use fresh `state` or `find` snapshots before interactions and verify every written value with `get value` or a fresh state.
- Treat SeaTable Slate rich-text fields as fragile. Any write must be verified after the popup closes; visible text inside the editor popup alone is not enough.
- Generate report content as plain paragraphs for Slate rich text. Do not emit Markdown markers such as `#`, `##`, `###`, `-`, `*`, `1.`, or fenced code blocks.
- When modifying an existing weekly report in `我的周报`, prefer reading the current text, composing the final full content offline, and writing it back through the Slate-compatible paste path. If this week's report already contains Markdown-style markers, rewrite the whole field into plain rich text instead of appending to it.
- If the standard replace flow makes the preview look correct but reopening the editor still shows stale Markdown, treat it as a Slate/React persistence failure and switch to the fallback path in `references/slate-editor.md`.
- If the OpenCLI flow cannot prove the field value persisted, do **not** submit. Stop and ask the user whether to retry or switch to a manual fallback.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WEEKLY_REPORT_URL` | Yes | 周报系统页面的完整 URL（不是 SeaTable 首页） |
| `SEATABLE_API_TOKEN` or `SEATABLE_API_TOKEN_FILE` | For API reads | SeaTable API token; use a local ignored file for the latter |

**First-time setup:** If `WEEKLY_REPORT_URL` is not set, instruct the user to configure it permanently.

URL 必须精确指向**周报系统**页面，而不是 SeaTable 首页或其他表。获取方式：在浏览器中打开周报系统，看到"周报填写"/"我的周报"等视图后，复制地址栏的完整 URL。通常格式为 `https://<host>/external-apps/<uuid>/`。

```bash
# Fish shell
set -Ux WEEKLY_REPORT_URL "https://inner-table.example.com/external-apps/<uuid>/"

# Bash/Zsh — add to ~/.bashrc or ~/.zshrc
export WEEKLY_REPORT_URL="https://inner-table.example.com/external-apps/<uuid>/"
```

For API reads, set one token source. `SEATABLE_API_TOKEN_FILE` may point to a local file such as `token.txt`; read it at runtime and never print it. If no API token is available, use the browser authentication fallback described below.

## Quick Reference

| Task | Reference |
|------|-----------|
| Activity analysis & content generation | [references/git-analysis.md](references/git-analysis.md) |
| Monthly aggregation & Xinrenxinshi KPI | [references/monthly-kpi.md](references/monthly-kpi.md) |
| SeaTable Slate editor operations | [references/slate-editor.md](references/slate-editor.md) |
| Navigation & authentication | [references/navigation.md](references/navigation.md) |

## Workflow

1. **Read existing report records via the SeaTable API** → see [sea-table-api.md](references/sea-table-api.md)
2. **Choose the period:** one week for a weekly report, all matching calendar-month rows for a monthly report.
3. **Analyze and deduplicate** activity by project and outcome, including parent-repo/submodule duplicates.
4. **Generate the target format:** SeaTable Slate paragraphs or a structured KPI summary.
5. **Write with OpenCLI** only when requested → see [navigation.md](references/navigation.md), [slate-editor.md](references/slate-editor.md), or [monthly-kpi.md](references/monthly-kpi.md).
6. **Verify** every field and total weight after writing. For a newly created SeaTable report, confirm the persisted row through the API after the browser reports success.
7. **Save a draft by default.** Final submit requires explicit user instruction.

## Tool Decision Rules

- `opencli-browser` governs browser operations; use `opencli browser <session> *` commands.
- Use `opencli browser state` or `opencli browser find` before each interaction; refs are only valid for the current snapshot.
- Prefer creating the current week's report in `周报填写` when the row does not exist yet.
- Opening an existing `我的周报` long-text cell may require a page-side `dblclick` dispatch. A normal single click on the table cell often only focuses the row and does not open the editor.
- Editing an **existing** rich-text cell in `我的周报` is higher risk than filling a blank field. Re-open and verify the rendered value after each edit.
- If this week's report already uses Markdown-style markers, normalize the whole field back to plain rich text before submit.
- If preview text and reopened editor text disagree, the reopened editor wins. Keep fixing until the reopened content is clean.
- Do not rely on popup-only evidence. If the form preview or table cell does not reflect the new content, the write did not persist.

## Report Content Format

Use `header_three` for project/section names and `paragraph` for work items. This produces visually distinct headings in SeaTable's Slate editor.

```javascript
// Slate node array structure
{ type: 'header_three', children: [{ text: 'arcs-sdk' }] }
{ type: 'paragraph',    children: [{ text: '完成事项 1' }] }
{ type: 'paragraph',    children: [{ text: '完成事项 2' }] }
{ type: 'paragraph',    children: [{ text: '' }] }   // blank separator
{ type: 'header_three', children: [{ text: 'uboot' }] }
{ type: 'paragraph',    children: [{ text: '完成事项 3' }] }
```

Keep items concise (one line each). Group by project, not by date. Do not use Markdown markers such as `###` or `-` in the final field value.
