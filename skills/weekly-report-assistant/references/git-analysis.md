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

### Step 1: Get Current User ID

```bash
glab api "/user" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"
```

For multiple GitLab hosts, use `--hostname <host>` to specify the target instance.

### Step 2: Fetch Events for the Past Week

```bash
SINCE=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d'))")

glab api "/users/{USER_ID}/events?after=${SINCE}&per_page=100" > /tmp/events_p1.json
```

If the user is highly active, fetch additional pages with `&page=2`, `&page=3`, etc.

### Step 3: Parse and Summarize

Group events by `project_id`. Key fields per event:

- **`action_name`** — what happened (`pushed to`, `opened`, `accepted`, etc.)
- **`target_type`** / **`target_title`** — the object acted on (MR, Issue, etc.)
- **`push_data.commit_title`** / **`push_data.ref`** — commit details for push events

Resolve project IDs to names for report headings:

```bash
glab api "/projects/{PROJECT_ID}" | python3 -c "import sys,json; print(json.load(sys.stdin)['name_with_namespace'])"
```

### Key Event Types

| action_name | target_type | Meaning |
|-------------|-------------|---------|
| `pushed to` | — | Pushed commits (check `push_data.commit_title`) |
| `pushed new` | — | Created a new branch |
| `opened` | `MergeRequest` | Created a merge request |
| `accepted` | `MergeRequest` | Merged a merge request |
| `closed` | `MergeRequest` | Closed a merge request |
| `opened` | `Issue` | Created an issue |
| `commented on` | `Note` | Left a comment |

### Filtering Tips

- Focus on `pushed to`, `opened MergeRequest`, and `accepted MergeRequest` for meaningful work items
- Ignore `deleted` branch events (cleanup noise)
- Deduplicate multiple pushes to the same branch — summarize as one item
- Prefer MR titles over individual commit messages (more descriptive)

## Mode 2: Local Git Log (Fallback)

Use when `glab` is not available. Only covers the **current repository**.

```bash
git log --all --author="$(git config user.name)" --since="7 days ago" \
  --format="%h %ad %s" --date=short
```

**Limitation:** Only sees commits in the current repo. For multiple repos, run in each repo or ask the user for additional context.

## Deduplication

Always read the previous week's report first. Remove items that overlap with already-reported work.

## Grouping

Organize by project/component (e.g., "Project A:", "CI/CD:"), not by date.
