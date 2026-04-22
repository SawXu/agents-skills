# SeaTable Slate Editor Operations

SeaTable uses a **Slate.js rich-text editor**. This is the most error-prone part of the workflow.

## The Golden Rule

> **Slate has an internal data model that is independent of the DOM.**
> Seeing text in the popup editor does not prove the field value was saved.
> The only acceptable success signal is that the rendered form preview or table cell reflects the updated content after the popup closes.

## Browser Boundary

This skill assumes browser actions are performed through the `opencli-adapter-author` skill.

- Use `opencli browser state` or `opencli browser find` before every interaction.
- Use `opencli browser click`, `type`, `keys`, and `get text/value` as the primary control surface.
- Use `opencli browser eval` for two narrow SeaTable exceptions only: dispatching `dblclick` on an existing long-text cell to open the editor, and dispatching a Slate-recognized paste-like event for full-content replacement.
- After any edit, close the popup and verify the rendered field value changed outside the editor.

## Hard Rule

- Prefer editing blank fields in `周报填写`; this is safer than rewriting an existing rich-text cell in `我的周报`.
- For existing `我的周报` content, do not rely on cursor positioning plus raw `type` append. Read the current text, build the final full content offline, replace the whole field, then verify.
- If verification fails at any point, do **not** submit the form.

## Opening the Slate Editor

In the `周报填写` form, rich-text fields show `编辑文本` as a placeholder. Open the field from the latest snapshot:

```bash
opencli browser state
opencli browser click 27   # example ref: 本周进展
```

In `我的周报`, first locate the row, then click or double-activate the long-text cell using the latest refs shown by `state`.

## Recommended Edit Loop

1. Open the target field popup.
2. For a blank field in `周报填写`, click inside the editable area and type or paste the content.
3. For an existing field in `我的周报`, read the current content first, then prepare the final full content outside the page.
4. Replace the whole field using the paste-like path below instead of appending one line with raw typing.
5. Close the popup with the header `X`.
6. Verify the outer form preview or table cell changed.
7. Re-open once if the edit was high risk and confirm the content is still present.

Example skeleton:

```bash
opencli browser state
opencli browser click 27
opencli browser click "[contenteditable='true']"
opencli browser keys Control+a
opencli browser keys Backspace
opencli browser type "[contenteditable='true']" "### 淘云扫描笔\n- 修复 avi_player 概率性音频卡顿问题。"
opencli browser click ".longtext-header-tool-item.dtable-icon-x"
opencli browser state
```

## Existing Record Full-Replacement Path

This is the most reliable path we observed for updating an existing `我的周报` rich-text cell.

1. Open the existing cell, using page-side `dblclick` dispatch if a normal click does not work.
2. Read the current content with `opencli browser get text "[contenteditable='true']"`.
3. Build the final full text outside the page.
4. Select the full editor content and dispatch a paste-like event with the final text.
5. Close the popup and verify the list-view cell contains the new unique text.

Example:

```bash
opencli browser eval "(() => {
  const editor = document.querySelector('[contenteditable=\"true\"]');
  if (!editor) return { ok: false, reason: 'no-editor' };
  editor.focus();
  const range = document.createRange();
  range.selectNodeContents(editor);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  const dt = new DataTransfer();
  dt.setData('text/plain', '### 淘云扫描笔\\n- 修复 avi_player 概率性音频卡顿问题。\\n\\n### ARCS SDK\\n- skills目录结构改为标准结构');
  const ev = new ClipboardEvent('paste', {
    clipboardData: dt,
    bubbles: true,
    cancelable: true
  });
  editor.dispatchEvent(ev);
  return { ok: true, text: editor.innerText };
})()"
opencli browser click ".longtext-header-tool-item.dtable-icon-x"
opencli browser state
```

Do not trust the popup text alone. The write only counts after the outer table cell reflects the new content.

## Content Shape

Keep the generated content simple so Slate is less likely to mangle it:

```text
### 项目名称
- 事项 1
- 事项 2

### 另一个项目
- 事项 3
```

After closing the popup, the field preview should show the section heading and bullet list content instead of `编辑文本`.

## Verification

Always verify after editing:

```bash
opencli browser state
opencli browser get text "div[title*='淘云扫描笔']" --nth 0
```

Use selectors that match the outer field preview or target table cell, not the popup editor itself.

For higher-risk edits, re-open the field and confirm the content remains:

```bash
opencli browser click 27
opencli browser get text "[contenteditable='true']"
opencli browser click ".longtext-header-tool-item.dtable-icon-x"
```

## Anti-Patterns

Avoid these for SeaTable Slate:

- assuming popup text means the field value is saved
- submitting immediately without checking the rendered preview
- appending one more bullet to an existing `我的周报` cell with raw `type` and assuming it persisted
- making a large replace inside `我的周报` and trusting a single observation
- using stale refs from before the editor popup opened
- reusing stale refs after navigation, popup close, or view switching

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Single-clicking an existing long-text cell in `我的周报` | Row gets focused but the editor does not open | Use a row-local `dblclick` dispatch, then refresh `state` |
| Typing into the popup and submitting immediately | Popup looks correct, but field preview may still be empty or stale | Close the popup and verify the rendered field value first |
| Appending to an existing report with `type` near the cursor | Text may appear in the popup but fail to persist after close | Read current text, compose final full content, then replace through the paste-like path |
| Reusing old refs after switching views | Clicks land on the wrong element or fail | Run `opencli browser state` again |
| Replacing a large existing report in one shot | Slate may keep stale structure or partial old content | Prefer blank-field creation or edit in smaller steps |
| Verifying only inside `[contenteditable]` | Misses persistence failures | Verify the outer preview or table cell after close |
| Ignoring ambiguous selectors | Writes may hit the wrong field | Narrow the selector or use a fresh numeric ref |
