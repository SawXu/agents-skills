# Activity Analysis & Content Generation

## Data Source Selection

**Priority:** glab API (GitLab Events) > local git log

Detect the available data source at the start of every report generation:

```bash
glab auth status 2>&1
```

- If `glab` is authenticated → use **glab API mode**
- Otherwise → fall back to **git log mode**

## Mode 1: glab API (Preferred)

GitLab Events API provides a **cross-project** view of all user activity, far more comprehensive than local git log.

### Step 1: Get Current User Info

```bash
glab api "/user" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('id:', d['id'])
print('email:', d['email'])
print('name:', d['name'])
"
```

Save the `id` and `email` — both are needed for filtering. Use `--hostname <host>` for non-default GitLab instances.

### Step 2: Fetch Events for the Past Week

```bash
SINCE=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d'))")

glab api "/users/{USER_ID}/events?after=${SINCE}&per_page=100" > /tmp/events_p1.json
```

If the user is highly active, fetch additional pages with `&page=2`, `&page=3`, etc.

### Step 3: Collect Authored Commits per Project

Events only tell you what was *pushed*. A push can include cherry-picked commits written by someone else. To get commits the user actually **authored**, fetch them directly per project using the `author` parameter, then filter client-side by `author_email`.

```bash
# For each project_id that had push events:
glab api "/projects/{PROJECT_ID}/repository/commits?author={USER_EMAIL}&since={SINCE}T00:00:00Z&per_page=100" \
  | python3 -c "
import sys, json
USER_EMAIL = '{USER_EMAIL}'
commits = json.load(sys.stdin)
for c in commits:
    # GitLab's author filter can be unreliable — always verify client-side
    if c['author_email'] == USER_EMAIL:
        print(c['id'][:8], c['title'])
"
```

**Critical:** Always verify `author_email == user_email` client-side. GitLab's `author` query parameter sometimes returns commits where the user is the committer but not the author (e.g. cherry-picks), so server-side filtering alone is not sufficient.

### Step 4: Collect Opened MRs

`opened MergeRequest` events are safe to include directly — opening an MR means the user is the author.

```bash
# From the events JSON already fetched:
python3 -c "
import json
events = json.load(open('/tmp/events_p1.json'))
mrs = [e for e in events if e['action_name'] == 'opened' and e.get('target_type') == 'MergeRequest']
for e in mrs:
    print(e['project_id'], e['target_title'])
"
```

### Key Event Types

| action_name | target_type | Meaning | Count as work? |
|-------------|-------------|---------|----------------|
| `pushed to` / `pushed new` | — | Pushed commits — **verify author_email per commit** | ⚠️ Only if authored by user |
| `opened` | `MergeRequest` | User created the MR | ✅ Yes |
| `accepted` | `MergeRequest` | User clicked Merge (may be someone else's code) | ❌ No |
| `closed` | `MergeRequest` | Closed an MR | ❌ No |
| `commented on` | `Note` | Left a comment | ❌ No |

**Two rules that must both be satisfied for a commit to count:**
1. It appears in the user's push events (the user pushed it)
2. Its `author_email` matches the user's email (the user wrote it)

Cherry-picked commits fail rule 2 — exclude them even if the user pushed them.

### Resolve Project Names

```bash
glab api "/projects/{PROJECT_ID}" | python3 -c "import sys,json; print(json.load(sys.stdin)['name_with_namespace'])"
```

## Mode 2: Local Git Log (Fallback)

Use when `glab` is not available. Only covers the **current repository**.

```bash
git log --all --author="$(git config user.name)" --since="7 days ago" \
  --format="%h %ad %s" --date=short
```

**Limitation:** Only sees commits in the current repo. For multiple repos, run in each repo or ask the user for additional context.

## Deduplication

Always read the previous week's report first. Remove items that overlap with already-reported work.

### Cross-Repo Submodule-Bump Deduplication

When a parent-repo commit bumps a submodule pointer, the parent commit and the matching submodule commit are **the same piece of work**. Listing both inflates the report.

**Rule:** if an authored commit in the parent repo modifies the submodule pointer (e.g. `system/uboot`, `soc/arcs/hal`), do not count it as an independent parent-repo work item. Fold it into the submodule's section, optionally noting the parent-side adoption (board/sample/driver glue) in the same bullet.

**How to detect:** for each authored parent-repo commit, fetch its diff and look for `Subproject commit` markers, or for changes to known submodule paths.

```bash
# For each commit SHA in the parent repo, mark whether any hunk touches a submodule pointer.
glab api "/projects/{PARENT_PROJECT_ID}/repository/commits/{SHA}/diff" \
  | python3 -c "
import sys, json
diffs = json.load(sys.stdin)
has_submod = any('Subproject commit' in (d.get('diff') or '') for d in diffs)
only_submod = has_submod and all('Subproject commit' in (d.get('diff') or '') for d in diffs)
print('SUBMODULE-ONLY' if only_submod else 'HAS-SUBMODULE-BUMP' if has_submod else 'INDEPENDENT')
"
```

**Categorization:**

| Category | Meaning | Where to list |
|----------|---------|---------------|
| `SUBMODULE-ONLY` | Parent commit only bumps the submodule pointer | Submodule section only — drop from parent |
| `HAS-SUBMODULE-BUMP` | Parent commit changes parent files **and** bumps the submodule | Submodule section, optionally with a parent-side adoption note |
| `INDEPENDENT` | Parent commit has no submodule-pointer change | Parent-repo section |

**Edge case — incidental bumps:** when the parent commit's substantive change is unrelated to any submodule commit that week (e.g. `fix(ipclsf): handle timeout` that incidentally bumps an unrelated submodule), keep it in the parent section. The rule's purpose is to avoid double-counting the *same* work, not to attribute every incidental bump to the submodule.

## Grouping

Organize by project/component (e.g., "arcs-sdk", "uboot"), not by date.

When building the Slate node array, use `header_three` for section/project names and `paragraph` for individual work items. Do not use `paragraph` for all lines — section headings rendered as paragraphs are visually indistinguishable from work items.

```javascript
// Correct
{ type: 'header_three', children: [{ text: 'arcs-sdk' }] }
{ type: 'paragraph',    children: [{ text: '合入 CherryUSB boot adb 后端' }] }

// Wrong
{ type: 'paragraph', children: [{ text: 'arcs-sdk' }] }
{ type: 'paragraph', children: [{ text: '合入 CherryUSB boot adb 后端' }] }
```
