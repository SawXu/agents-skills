# Git Commit Analysis

## Getting Commits

```bash
# Get commits for the past week by current user
git log --all --author="$(git config user.name)" --since="7 days ago" \
  --format="%h %ad %s%n%b---" --date=short
```

## Deduplication

Always read the previous week's report first. Remove items that overlap with already-reported work.

## Grouping

Organize by project/component (e.g., "Project A:", "CI/CD:"), not by date.
