# SeaTable Slate Editor Operations

SeaTable uses a **Slate.js rich-text editor**. This is the most error-prone part.

## The Golden Rule

> **Slate has an internal data model that is independent of the DOM.**
> Direct DOM manipulation (`innerHTML`, `insertHTML`, `execCommand`) will NOT persist.
> Only keyboard input, Slate-recognized paste events, and Slate API calls are saved.

## Tool Boundary: `playwright-cli` vs `opencli-browser`

### What actually worked in practice

- `opencli browser type` can make text appear inside the popup editor, but SeaTable may still treat the field as empty during submit.
- `opencli-browser` can persist **new field creation** if you trigger a Slate-recognized paste-like path and then confirm the form preview changed from `编辑文本` to rendered paragraph nodes.
- Replacing content inside an **existing** rich-text cell in `我的周报` is not reliable with `opencli-browser`. SeaTable may merge stale nodes and keep part of the old content.
- `playwright-cli run-code` remains the recommended path for all replace/append/delete operations that must be correct on first try.

### Hard rule

- Use `playwright-cli` for replacing or cleaning existing Slate content.
- Use `opencli-browser` only when the user explicitly requires it or when the field is blank and you can verify the rendered form preview changed after edit.

## Critical `eval` Limitations

`playwright-cli eval` does **not** support:
- `const` / `let` — use `var` only
- Multi-line JS expressions — use `run-code --filename=` instead

For any non-trivial JS (paste, selection, complex reads), always write to a file and use `run-code`:

```bash
cat > /tmp/my-script.js << 'EOF'
async page => {
  await page.evaluate(function() {
    // your JS here using var, not const/let
  });
}
EOF
playwright-cli run-code --filename=/tmp/my-script.js
```

## Opening the Slate Editor (周报填写 Form)

In the 周报填写 form, rich-text fields show "编辑文本" as a placeholder. Click it to open the editor:

```bash
# For 本周进展 (first rich-text field)
playwright-cli click "locator('div').filter({ hasText: /^编辑文本$/ }).first()"

# For 下周计划 (second rich-text field)
playwright-cli click "locator('div').filter({ hasText: /^编辑文本$/ }).nth(2)"
```

## Opening the Slate Editor (我的周报 List)

In the report list view, double-click the long-text cell to open the editor:

```bash
cat > /tmp/open-editor.js << 'EOF'
async page => {
  await page.evaluate(function() {
    var rows = document.querySelectorAll('.dtable-result-table-row');
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].textContent.includes('TARGET_IDENTIFIER')) {
        var cells = rows[i].querySelectorAll('.dtable-result-table-long-text-cell');
        if (cells[0]) {
          cells[0].dispatchEvent(new MouseEvent('dblclick', {bubbles: true, cancelable: true}));
        }
        break;
      }
    }
    return 'done';
  });
}
EOF
playwright-cli run-code --filename=/tmp/open-editor.js
```

## Focusing the Editor Before Paste

**This step is required.** Simply clicking the field to open the editor is not enough — paste will silently fail unless you physically click inside the `[contenteditable]` area:

```bash
# Get editor position first
playwright-cli eval "JSON.stringify(document.querySelector('[contenteditable=true]').getBoundingClientRect())"

# Click inside the editor (use center X, top Y + a few pixels)
playwright-cli mousemove 640 120
playwright-cli mousedown
playwright-cli mouseup
```

## Replacing All Content (Recommended Method)

Write the paste script to a file and use `run-code`. This is the **only reliable method** for bulk content insertion:

```bash
cat > /tmp/paste-content.js << 'EOF'
async page => {
  await page.evaluate(function() {
    var editor = document.querySelector('[contenteditable=true]');
    editor.focus();
    var range = document.createRange();
    range.selectNodeContents(editor);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);

    var html = '<h3>Section Title</h3><ul><li><p>Item 1</p></li><li><p>Item 2</p></li></ul>';
    var dt = new DataTransfer();
    dt.setData('text/html', html);
    var pasteEvent = new ClipboardEvent('paste', {
      clipboardData: dt, bubbles: true, cancelable: true
    });
    editor.dispatchEvent(pasteEvent);
    return 'pasted';
  });
}
EOF
playwright-cli run-code --filename=/tmp/paste-content.js
```

The HTML format for `html` variable:

```html
<h3>Project Name</h3>
<ul>
  <li><p>Task item one</p></li>
  <li><p>Task item two</p></li>
</ul>
<h3>Another Project</h3>
<ul>
  <li><p>Task item three</p></li>
</ul>
```

## `opencli-browser` Path for New Empty Fields

This path is acceptable when editing a blank field in `周报填写` and the user explicitly wants browser control via `opencli-browser`.

1. Open the field popup.
2. Trigger a page-side paste event against `[contenteditable=true]`.
3. Close the popup with the header `X`.
4. Verify the form field no longer shows `编辑文本`; it must render `<p>` nodes in the form preview.

Example:

```bash
opencli browser click 27
opencli browser eval "(() => {
  var editor = document.querySelector('[contenteditable=true]');
  if (!editor) return { ok: false, reason: 'no-editor' };
  editor.focus();
  var range = document.createRange();
  range.selectNodeContents(editor);
  var sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  var dt = new DataTransfer();
  dt.setData('text/plain', '### 淘云扫描笔\n- 修复 avi_player 概率性音频卡顿问题。');
  var ev = new ClipboardEvent('paste', {
    clipboardData: dt, bubbles: true, cancelable: true
  });
  editor.dispatchEvent(ev);
  return { ok: true, text: editor.innerText };
})()"
opencli browser click ".longtext-header-tool-item.dtable-icon-x"
opencli browser state
```

If `opencli browser state` still shows `编辑文本`, the write did **not** persist. Do not submit.

## `opencli-browser` Anti-Patterns

Avoid these for SeaTable Slate:

- `opencli browser type [contenteditable] ...` as the only write step
- `Ctrl+A` + `Backspace` to clear existing content
- `document.execCommand('insertHTML')` or `innerHTML = ...` as a persistence mechanism
- assuming that popup editor text means the field value is saved

These can leave the popup showing new text while the form still submits as empty, or merge old and new content in existing records.

## Reading Editor Content (Verification)

Always verify after paste:

```bash
playwright-cli eval "document.querySelector('[contenteditable=true]').innerText.replace(/\uFEFF/g,'').substring(0, 500)"
```

For full Slate DOM structure:

```bash
cat > /tmp/read-editor.js << 'EOF'
async page => {
  return await page.evaluate(function() {
    var editor = document.querySelector('[contenteditable=true]');
    var children = Array.from(editor.children);
    return children.map(function(c, i) {
      if (c.tagName === 'UL') {
        var items = c.querySelectorAll(':scope > li');
        var texts = Array.from(items).map(function(li) {
          return '  - ' + li.textContent.substring(0, 60);
        });
        return i + ' UL (' + items.length + ' items):\n' + texts.join('\n');
      }
      return i + ' ' + c.tagName + ': ' + c.textContent.replace(/\uFEFF/g,'').substring(0, 60);
    }).join('\n');
  });
}
EOF
playwright-cli run-code --filename=/tmp/read-editor.js
```

## Appending Content (Keyboard Method)

Place cursor at end of last list item, then type new sections:

```bash
cat > /tmp/place-cursor.js << 'EOF'
async page => {
  await page.evaluate(function() {
    var editor = document.querySelector('[contenteditable=true]');
    var lastUl = editor.querySelectorAll('ul');
    var targetUl = lastUl[lastUl.length - 1];
    var lastLi = targetUl.querySelector('li:last-child p');
    var range = document.createRange();
    range.selectNodeContents(lastLi);
    range.collapse(false);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    return 'cursor placed';
  });
}
EOF
playwright-cli run-code --filename=/tmp/place-cursor.js

# Exit list, then add new section
playwright-cli press Enter
playwright-cli press Enter
playwright-cli keyboard type "### New Section Title"
playwright-cli press Enter
playwright-cli keyboard type "- First item"
playwright-cli press Enter
playwright-cli keyboard type "Second item"
```

## Closing the Editor

```bash
playwright-cli press Escape
```

Slate auto-saves when the editor loses focus. No explicit save button exists.

With `opencli-browser`, the most reliable close action is the popup header `X`:

```bash
opencli browser click ".longtext-header-tool-item.dtable-icon-x"
```

After closing, immediately verify the form preview or table cell text changed as expected.

## Deleting Content

Select a range with JS, then press Backspace:

```bash
cat > /tmp/select-range.js << 'EOF'
async page => {
  await page.evaluate(function() {
    var editor = document.querySelector('[contenteditable=true]');
    var badElement = editor.children[2]; // first element to delete
    var range = document.createRange();
    range.setStartBefore(badElement);
    range.setEndAfter(editor.lastElementChild);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    return 'selected';
  });
}
EOF
playwright-cli run-code --filename=/tmp/select-range.js
playwright-cli press Backspace
```

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using `innerHTML =` or `insertHTML` | Content shows in DOM but doesn't persist after reload | Use `run-code` paste method only |
| Using `const`/`let` in `eval` | SyntaxError | Use `var` or write to file and use `run-code` |
| Multi-line JS in `eval` | SyntaxError | Write to file and use `run-code --filename=` |
| Not clicking inside `[contenteditable]` before paste | Paste silently fails (editor stays empty) | Use `mousemove + mousedown + mouseup` on editor coords |
| Using `keyboard type` with `-` prefix on every line | Each line indents one more level (nested lists) | Use `-` only for the first item |
| Not verifying after edit | Silent data loss | Always read editor `innerText` after paste |
| Ctrl+A then Backspace to clear | Only partial deletion in Slate | Use JS range selection then Backspace |
| Using `opencli browser type` and submitting immediately | Popup shows text, but required field still submits as empty | Use the paste-like path and verify form preview changed |
| Editing existing `我的周报` content with `opencli-browser` | Old nodes may remain and merge with new text | Replace with `playwright-cli` instead |
