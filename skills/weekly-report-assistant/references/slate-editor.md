# SeaTable Slate Editor Operations

SeaTable uses a **Slate.js rich-text editor**. This is the most error-prone part.

## The Golden Rule

> **Slate has an internal data model that is independent of the DOM.**
> Direct DOM manipulation (`innerHTML`, `insertHTML`, `execCommand`) will NOT persist.
> Only keyboard input, Slate-recognized paste events, and Slate API calls are saved.

## Opening the Editor

The report list view is read-only. To edit a record's long-text cell:

```javascript
// Double-click the target cell to open Slate editor
agent-browser eval --stdin <<'EVALEOF'
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
'done'
EVALEOF
```

## Reading Editor Content (Verification)

```javascript
// Read full Slate structure
agent-browser eval --stdin <<'EVALEOF'
var editor = document.querySelector('[contenteditable="true"]');
var children = Array.from(editor.children);
children.map(function(c, i) {
  var detail = '';
  if (c.tagName === 'UL') {
    var items = c.querySelectorAll(':scope > li');
    detail = ' (' + items.length + ' items)';
    var texts = Array.from(items).map(function(li) {
      return '  - ' + li.textContent.substring(0, 60);
    });
    return i + ' ' + c.tagName + detail + ':\n' + texts.join('\n');
  }
  return i + ' ' + c.tagName + ': ' + c.textContent.replace(/\uFEFF/g,'').substring(0, 60);
}).join('\n');
EVALEOF
```

## Appending Content

**Step 1:** Place cursor at the end of the last list item in existing content:

```javascript
agent-browser eval --stdin <<'EVALEOF'
var editor = document.querySelector('[contenteditable="true"]');
var lastUl = editor.querySelectorAll('ul');
var targetUl = lastUl[lastUl.length - 1];
var lastLi = targetUl.querySelector('li:last-child p');
var range = document.createRange();
range.selectNodeContents(lastLi);
range.collapse(false);
var sel = window.getSelection();
sel.removeAllRanges();
sel.addRange(range);
'cursor placed'
EVALEOF
```

**Step 2:** Use keyboard to type new content. Slate recognizes these markdown shortcuts:
- `Enter` in a list item creates a new list item (same level)
- `Enter` twice exits the list
- `### ` at line start creates H3 heading (type the text, it auto-converts)

**Step 3:** For adding a new section (H3 + list):

```bash
# Exit current list, then type heading
agent-browser press Enter
agent-browser press Enter  # exits list to paragraph
agent-browser keyboard type "### New Section Title"
agent-browser press Enter
agent-browser keyboard type "- First item"   # markdown shortcut creates UL
agent-browser press Enter                    # new list item auto-created
agent-browser keyboard type "Second item"    # type text only, no dash needed
```

**IMPORTANT:** If Slate doesn't convert `### ` to H3 automatically, the alternative is:
1. Type the heading text as a paragraph
2. Select it
3. Use the toolbar dropdown to change to "Heading 3"

## Replacing All Content

Use clipboard paste with HTML — this is the ONLY reliable way to replace content in Slate:

```javascript
agent-browser eval --stdin <<'EVALEOF'
var editor = document.querySelector('[contenteditable="true"]');
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
'pasted'
EVALEOF
```

**WARNING:** Paste replaces selected content but may also leave residual nodes. Always verify with the reading pattern above and clean up with keyboard (select + backspace) if needed.

## Deleting Content

Use JS to select a range, then keyboard Backspace:

```javascript
// Select from element N to end, then delete
agent-browser eval --stdin <<'EVALEOF'
var editor = document.querySelector('[contenteditable="true"]');
var badElement = editor.children[N]; // index of first element to delete
var range = document.createRange();
range.setStartBefore(badElement);
range.setEndAfter(editor.lastElementChild);
var sel = window.getSelection();
sel.removeAllRanges();
sel.addRange(range);
'selected'
EVALEOF

agent-browser press Backspace
```

## Saving

Slate auto-saves when you close the editor modal (click outside or press Escape). There is no explicit save button for cell content.

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using `innerHTML =` or `insertHTML` | Content shows in DOM but doesn't persist after reload | Use keyboard input or paste events only |
| Using `keyboard type` with `-` prefix on every line | Each line indents one more level (nested lists) | Use `-` only for the first item; after Enter, Slate auto-creates next `<li>` |
| Not verifying after edit | Silent data loss | Always read editor structure after modification |
| Ctrl+A then Backspace to clear | Only partial deletion in Slate | Use JS range selection then Backspace |
| Multiple Ctrl+Z to undo | Slate batches keyboard input as single undo step | May not fully undo; refresh page to get server-saved version |
