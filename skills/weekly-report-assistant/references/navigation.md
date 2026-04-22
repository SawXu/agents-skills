# Navigation & Authentication

This reference assumes the agent is already using the `opencli-adapter-author` skill as the top-level OpenCLI workflow.

- Start with `opencli doctor` if browser automation has not been validated in the current environment.
- Use `opencli browser state` before interacting, and take a fresh snapshot after every page transition.
- Prefer numeric refs from `state` or `find`; only fall back to CSS selectors when a ref is not available yet.
- In `我的周报`, if a long-text cell refuses to open through a normal click, use a narrow page-side `dblclick` dispatch for that cell only, then refresh state immediately.

## Opening the Browser

```bash
opencli browser open "$WEEKLY_REPORT_URL" --focus
opencli browser state
```

If the page redirects to a login page, proceed with SSO below.

## SSO Login

Click the "单点登录" link to trigger WeChat Work QR code login:

```bash
opencli browser find --css "a" --limit 20
opencli browser click "a[title='单点登录']"
opencli browser screenshot ~/wechat-qr.png
```

Wait for the user to scan, then verify the redirect landed on the weekly report system:

```bash
opencli browser wait text "周报" --timeout 20000
opencli browser state
```

## View Switching

The system has two main views: **周报填写** (new report form) and **我的周报** (my report history).

**View selection logic:**

1. Click `我的周报` to check if the current week's record already exists.
2. If the current week's report **exists** → locate and edit it in place.
3. If the current week's report **does not exist** → switch to `周报填写` to create a new one.

Switch views by clicking the view name in the left sidebar:

```bash
opencli browser state
opencli browser click 2   # example ref: 我的周报
opencli browser state
opencli browser click 1   # example ref: 周报填写
```

> Numeric refs are examples only. Always refresh them from the latest `state` output.

## 周报填写 Form Structure

When creating a new report, the form contains these fields:

| Field | Type | Required |
|-------|------|----------|
| 日期 | Date (auto-filled with today) | Yes |
| 本周进展 | Rich text (Slate editor) | Yes |
| 下周计划 | Rich text (Slate editor) | Yes |
| 风险 | Rich text (Slate editor) | No |
| 填写人 | Link to record (person selector) | Yes |

Open a rich-text field by clicking its `编辑文本` placeholder:

```bash
opencli browser state
opencli browser click 27   # example ref: 本周进展
```

Select the `填写人` by clicking `链接已有记录`, then the person's name in the picker. A typical flow is:

```bash
opencli browser state
opencli browser click 30
opencli browser click "div[title='徐宪辉']" --nth 0
opencli browser click "button[aria-label='Close']"
opencli browser state
```

Verify the selected person is rendered in the form before continuing.

## Existing Record Editing

When the current week's report already exists:

1. Open `我的周报`
2. Locate the row by title such as `2026-04-22-徐宪辉`
3. Open the target long-text cell
4. If this week's content still uses Markdown-style markers, rewrite the whole field into plain rich text via the guarded path in `slate-editor.md`
5. If preview and reopened content disagree after the normal replace path, switch to the fallback path in `slate-editor.md`
6. Close the popup and verify the table cell text changed

Locate the row with `find` first:

```bash
opencli browser find --css "div[title='2026-04-22-徐宪辉']" --limit 3
```

Then inspect the surrounding table structure before clicking. If the cell target is ambiguous, refresh `state` and select by the new numeric ref.

If a normal click does not open the rich-text popup, use a row-local double-click dispatch:

```bash
opencli browser eval "(() => {
  const row = [...document.querySelectorAll('.dtable-result-table-row')]
    .find(r => r.textContent.includes('2026-04-22-徐宪辉'));
  if (!row) return { ok: false, reason: 'row-not-found' };
  const cell = row.querySelector('.dtable-result-table-long-text-cell');
  if (!cell) return { ok: false, reason: 'cell-not-found' };
  cell.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, detail: 2 }));
  return { ok: true, text: cell.textContent.slice(0, 80) };
})()"
opencli browser state
```

After the popup opens, discard all earlier refs. The editor dialog creates a new interactive subtree and stale refs are common.

## Submit & Confirmation

Click the submit button after all required fields are filled:

```bash
opencli browser state
opencli browser click 53   # example ref: 提交
opencli browser wait text "感谢提交表单!" --timeout 10000
```

After submit, switch to `我的周报` and verify that the row `YYYY-MM-DD-姓名` exists and contains the expected field previews.
