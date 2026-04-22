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
- Final content must be plain paragraphs. Do not keep Markdown markers such as `###`, `-`, `*`, `1.`, or backticks in the saved field.
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
4. If this week's report still contains Markdown-style markers, convert the entire field to plain rich text before saving.
5. Replace the whole field using the paste-like path below instead of appending one line with raw typing.
6. Close the popup with the header `X`.
7. Verify the outer form preview or table cell changed.
8. Re-open once if the edit was high risk and confirm the content is still present.

Example skeleton:

```bash
opencli browser state
opencli browser click 27
opencli browser click "[contenteditable='true']"
opencli browser keys Control+a
opencli browser keys Backspace
opencli browser type "[contenteditable='true']" "淘云扫描笔\n修复 avi_player 概率性音频卡顿问题。\n\nARCS SDK\n整理 skills 标准目录结构。"
opencli browser click ".longtext-header-tool-item.dtable-icon-x"
opencli browser state
```

## Existing Record Full-Replacement Path

This is the most reliable path we observed for updating an existing `我的周报` rich-text cell.

1. Open the existing cell, using page-side `dblclick` dispatch if a normal click does not work.
2. Read the current content with `opencli browser get text "[contenteditable='true']"`.
3. If the current content includes Markdown-style markers such as `###` or list prefixes, plan a full normalization instead of an incremental edit.
4. Build the final full text outside the page as plain paragraphs.
5. Select the full editor content and dispatch a paste-like event with the final text.
6. Close the popup and verify the list-view cell contains the new unique text.
7. Re-open the same cell once. If old Markdown still appears, the replace only changed the DOM layer and you must use the fallback below.

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
  dt.setData('text/plain', '淘云扫描笔\\n修复 avi_player 概率性音频卡顿问题。\\n\\nARCS SDK\\nskills 目录结构改为标准结构。');
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

## Stubborn Existing Record Fallback

Use this only when the normal full-replacement path appears to work, but reopening the editor still shows stale Markdown or duplicated old content.

### Why this happens

In this failure mode, SeaTable keeps multiple layers out of sync:

- the visible DOM inside `[contenteditable='true']`
- the Slate value stored in `editor.children` / component `state.value`
- the popup owner's plain-text `props.value`

If you only update the DOM layer, the table preview may look cleaner for a moment, but reopening the editor can resurrect the old Markdown payload.

### Fallback Steps

1. Open the cell and confirm reopening still shows stale Markdown.
2. In `opencli browser eval`, locate the React class component above the editor that exposes `state.value`, `editor.children`, and `onChange`.
3. Replace the editor value with the final paragraph array.
4. Keep the owner's plain-text `props.value` in sync with the same content.
5. Call `onChange(desiredValue)` and mark the component as changed.
6. Close the popup, verify the outer preview, then re-open to ensure the Markdown residue is gone.

Example:

```bash
opencli browser eval "(() => {
  const desired = [
    { type: 'paragraph', children: [{ text: 'ARCS SDK' }] },
    { type: 'paragraph', children: [{ text: 'skills目录结构改为标准结构' }] },
    { type: 'paragraph', children: [{ text: '淘云扫描笔' }] },
    { type: 'paragraph', children: [{ text: '修复 avi_player 概率性音频卡顿问题。' }] },
    { type: 'paragraph', children: [{ text: '提升在线视频帧率并关闭视频页抗锯齿，优化画面流畅度。' }] },
    { type: 'paragraph', children: [{ text: 'UBOOT' }] },
    { type: 'paragraph', children: [{ text: '适配 CherryUSB 改为在 PSRAM 上运行，支持自升级。' }] }
  ];
  const desiredText = 'ARCS SDK\n\nskills目录结构改为标准结构\n\n淘云扫描笔\n\n修复 avi_player 概率性音频卡顿问题。\n\n提升在线视频帧率并关闭视频页抗锯齿，优化画面流畅度。\n\nUBOOT\n\n适配 CherryUSB 改为在 PSRAM 上运行，支持自升级。';

  const editorEl = document.querySelector('[contenteditable=\"true\"]');
  const fiberKey = Object.keys(editorEl).find(k => k.startsWith('__reactFiber'));
  let fiber = editorEl[fiberKey];
  let inst = null;

  for (; fiber; fiber = fiber.return) {
    if (fiber.stateNode && fiber.stateNode.onChange && fiber.stateNode.state && fiber.stateNode.state.value) {
      inst = fiber.stateNode;
      break;
    }
  }
  if (!inst) return { ok: false, reason: 'component-not-found' };

  inst.editor.children = desired;
  inst.editor.selection = { anchor: { path: [0, 0], offset: 0 }, focus: { path: [0, 0], offset: 0 } };
  inst.props.value = desiredText;
  inst.onChange(desired);
  inst.contentChanged = true;

  return { ok: true, text: editorEl.innerText };
})()"
```

This fallback is intentionally narrow: use it for a stubborn existing `我的周报` cell, not for blank fields in `周报填写`.

## Content Shape

Keep the generated content simple so Slate is less likely to mangle it:

```text
项目名称
事项 1
事项 2

另一个项目
事项 3
```

Use blank lines to separate project groups. If you need more visual hierarchy, keep it to short standalone section lines rather than Markdown syntax.

After closing the popup, the field preview should show the expected project names and work items instead of `编辑文本`.

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
- appending one more line to an existing `我的周报` cell with raw `type` and assuming it persisted
- making a large replace inside `我的周报` and trusting a single observation
- trusting a cleaned-up preview when reopening still shows stale Markdown
- leaving Markdown markers like `###` or `-` in the final saved field and assuming SeaTable will render them well
- using stale refs from before the editor popup opened
- reusing stale refs after navigation, popup close, or view switching

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Single-clicking an existing long-text cell in `我的周报` | Row gets focused but the editor does not open | Use a row-local `dblclick` dispatch, then refresh `state` |
| Typing into the popup and submitting immediately | Popup looks correct, but field preview may still be empty or stale | Close the popup and verify the rendered field value first |
| Appending to an existing report with `type` near the cursor | Text may appear in the popup but fail to persist after close | Read current text, compose final full content, then replace through the paste-like path |
| Preview looks clean but reopening still shows old Markdown | DOM changed, but Slate value or owner `props.value` stayed stale | Use the React-state fallback and re-open again |
| Leaving this week's report in Markdown style | SeaTable may show raw markers or broken layout | Rewrite the whole field as plain rich text and verify outside the popup |
| Reusing old refs after switching views | Clicks land on the wrong element or fail | Run `opencli browser state` again |
| Replacing a large existing report in one shot | Slate may keep stale structure or partial old content | Prefer blank-field creation or edit in smaller steps |
| Verifying only inside `[contenteditable]` | Misses persistence failures | Verify the outer preview or table cell after close |
| Ignoring ambiguous selectors | Writes may hit the wrong field | Narrow the selector or use a fresh numeric ref |
