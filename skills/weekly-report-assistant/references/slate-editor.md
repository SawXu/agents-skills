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
- Use `opencli browser eval` only for read-only inspection. Do not rely on DOM mutation inside `eval` as a persistence mechanism.
- After any edit, close the popup and verify the rendered field value changed outside the editor.

## Hard Rule

- Prefer editing blank fields in `周报填写`; this is safer than rewriting an existing rich-text cell in `我的周报`.
- For existing content, make the smallest possible change, then re-open and verify before continuing.
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
2. Click inside the editable area.
3. Use `Control+a` only when the field is expected to be fully replaced.
4. Use `Backspace` to clear if needed.
5. Type the new content.
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
opencli browser type "[contenteditable='true']" "### 淘云扫描笔\n- 修复 avi_player 概率性音频卡顿问题。"
opencli browser click ".longtext-header-tool-item.dtable-icon-x"
opencli browser state
```

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
- making a large replace inside `我的周报` and trusting a single observation
- using `opencli browser eval` to mutate the DOM and treating that as durable persistence
- reusing stale refs after navigation, popup close, or view switching

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Typing into the popup and submitting immediately | Popup looks correct, but field preview may still be empty or stale | Close the popup and verify the rendered field value first |
| Reusing old refs after switching views | Clicks land on the wrong element or fail | Run `opencli browser state` again |
| Replacing a large existing report in one shot | Slate may keep stale structure or partial old content | Prefer blank-field creation or edit in smaller steps |
| Verifying only inside `[contenteditable]` | Misses persistence failures | Verify the outer preview or table cell after close |
| Ignoring ambiguous selectors | Writes may hit the wrong field | Narrow the selector or use a fresh numeric ref |
