# Monthly Summary & Xinrenxinshi KPI

## Monthly Aggregation

Read every `周报` row for the requested person and calendar month through the SeaTable API. Sort by date, then consolidate repeated plans and carry-over work into the final outcome rather than listing the same item every week.

Group by project or outcome, not by week. Distinguish completed work from pending plans and risks. Do not claim a planned item was completed unless a later weekly entry reports the result.

## KPI Structure

When converting the month into KPI content:

- Use 3-5 indicators when the page permits; preserve existing indicator count unless the user requests changes.
- If the user supplies weights, use them exactly and verify the total is 100%.
- If weights or indicator names are missing, ask one short question instead of guessing.
- Put the indicator title in the name field when editable. If the name is locked or displays `-`, start `行动与结果` with a full-width bracket title such as `【SDK/HAL 基础能力建设】`.
- Format each textarea with numbered sections, a short subsection heading, and one outcome-focused paragraph.

Example:

```text
【SDK/HAL 基础能力建设】

1. 跨平台与构建质量
支持 macOS ARM64 编译及 setup，增加 Windows/Mac 编译验证；将 linker orphan section 改为报错并补齐链接脚本处理。

2. 稳定性与可观测性
细化 AP WDT、CP WDT、AON WDT 等复位原因，完善日志输出及板端测试。
```

## OpenCLI Workflow

1. Load `opencli-browser` and run `opencli doctor`.
2. Open the user-provided KPI URL in a stable named session.
3. Run `state`; verify the employee, month, workflow stage, existing indicator count, and available fields.
4. Use `type` for Xinrenxinshi number inputs and textareas if `fill` reports `not_editable`.
5. For replacement, focus the textarea, send `Control+a`, then type the complete formatted content.
6. Run `get value` for every weight and textarea.
7. Confirm the page displays a total weight of `100%`.
8. Click `保存草稿`, wait, and verify both the persisted values and the success message.

Refs are snapshot-specific. Refresh `state` after reopening the page or after navigation.

## Submission Boundary

Saving a draft is reversible; final submission advances the performance workflow. **Default to `保存草稿` and never click `提交` unless the user explicitly asks to submit after reviewing the content.** Report any locked or blank indicator names to the user.
