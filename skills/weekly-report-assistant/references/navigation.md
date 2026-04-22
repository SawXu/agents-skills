# Navigation & Authentication

This reference documents both `playwright-cli` and `opencli-browser` paths.

- Prefer `playwright-cli` if the task will definitely enter SeaTable Slate rich-text editing.
- `opencli-browser` is acceptable for navigation, view switching, row lookup, and verifying that submission succeeded.
- If using `opencli-browser`, always `state` before acting and refresh refs after every page transition.

## Opening the Browser

```bash
playwright-cli open "$WEEKLY_REPORT_URL"
```

```bash
opencli browser open "$WEEKLY_REPORT_URL" --focus
opencli browser state
```

If the page redirects to a login page, proceed with SSO below.

## SSO Login

Click the "单点登录" link to trigger WeChat Work QR code login:

```bash
playwright-cli click "getByRole('link', { name: '单点登录' })"
playwright-cli screenshot --filename=~/wechat-qr.png
xdg-open ~/wechat-qr.png   # opens QR image for the user to scan
```

Wait for the user to scan, then verify the redirect landed on the weekly report system.

## Session Persistence

Save auth state after a successful login so future runs skip the QR scan:

```bash
playwright-cli state-save
```

## View Switching

The system has two main views: **周报填写** (new report form) and **我的周报** (my report history).

**View selection logic:**

1. Click "我的周报" to check if the current week's record already exists
2. If the current week's report **exists** → locate and edit it in place
3. If the current week's report **does not exist** → switch to "周报填写" to create a new one

Switch views by clicking the view name in the left sidebar:

```bash
playwright-cli click "getByText('我的周报')"
playwright-cli click "getByText('周报填写')"
```

```bash
opencli browser click 2   # 我的周报
opencli browser click 1   # 周报填写
```

> **Note:** Clicking by text is more reliable than using CSS class selectors like `.view-item`.

## 周报填写 Form Structure

When creating a new report, the form contains these fields:

| Field | Type | Required |
|-------|------|----------|
| 日期 | Date (auto-filled with today) | Yes |
| 本周进展 | Rich text (Slate editor) | Yes |
| 下周计划 | Rich text (Slate editor) | Yes |
| 风险 | Rich text (Slate editor) | No |
| 填写人 | Link to record (person selector) | Yes |

Open a rich-text field by clicking its "编辑文本" placeholder:

```bash
playwright-cli click "locator('div').filter({ hasText: /^编辑文本$/ }).first()"
```

With `opencli-browser`, first take a fresh snapshot and then click the numeric ref for the desired placeholder:

```bash
opencli browser state
opencli browser click 27   # example: 本周进展
```

Select the 填写人 by clicking "链接已有记录", then clicking the person's name in the dropdown.

With `opencli-browser`, the reliable path is:

```bash
opencli browser click 30
opencli browser click "div[title='徐宪辉']" --nth 0
opencli browser click "button[aria-label='Close']"
```

Verify the selected person is rendered in the form before continuing.

## Existing Record Editing

When the current week's report already exists:

1. Open `我的周报`
2. Locate the row by title such as `2026-04-22-徐宪辉`
3. Open the target long-text cell
4. Edit via the Slate-safe path in `slate-editor.md`

`opencli-browser` can locate the row reliably:

```bash
opencli browser find --css "div[title='2026-04-22-徐宪辉']" --limit 3
```

For row-cell opening, a page-side double-click is usually required:

```bash
opencli browser eval "(() => {
  var rows = [...document.querySelectorAll('.dtable-result-table-row')];
  var row = rows.find(r => r.textContent.includes('2026-04-22-徐宪辉'));
  if (!row) return { ok: false };
  var cells = row.querySelectorAll('.dtable-result-table-long-text-cell');
  if (!cells[0]) return { ok: false, reason: 'no-cell' };
  cells[0].dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, detail: 2 }));
  return { ok: true };
})()"
```

After opening, verify the editor header shows the expected column name before modifying anything.

## Submit & Confirmation

Click the submit button after all required fields are filled:

```bash
playwright-cli click "getByRole('button', { name: '提交' })"
```

Success is confirmed when the page shows **"感谢提交表单!"**.

`opencli-browser` confirmation:

```bash
opencli browser click 53   # example ref for 提交
opencli browser wait text "感谢提交表单!" --timeout 10000
```

After submit, switch to `我的周报` and verify that the row `YYYY-MM-DD-姓名` exists.
