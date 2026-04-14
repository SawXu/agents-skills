# Navigation & Authentication

## Opening the Browser

```bash
playwright-cli open "$WEEKLY_REPORT_URL"
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

Select the 填写人 by clicking "链接已有记录", then clicking the person's name in the dropdown.

## Submit & Confirmation

Click the submit button after all required fields are filled:

```bash
playwright-cli click "getByRole('button', { name: '提交' })"
```

Success is confirmed when the page shows **"感谢提交表单!"**.
