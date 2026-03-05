## Purpose

LISTENAI's AI coding assistant skills collection. Pure documentation repo — no build/test commands.

- **GitHub**: [LISTENAI/skills](https://github.com/LISTENAI/skills)
- **License**: MIT

## Repository Structure

```
listenai-skills/
├── .claude-plugin/
│   └── marketplace.json   # Claude Code plugin marketplace manifest
├── skills/                # Agent Skills (agentskills format)
│   └── <skill-name>/
│       ├── SKILL.md       # Required — entry point with frontmatter
│       └── references/    # Optional — sub-files loaded on-demand
├── AGENTS.md              # Agent instructions (source of truth)
├── CLAUDE.md -> AGENTS.md # Symlink for Claude Code
├── LICENSE
└── README.md
```

## MANDATORY: Before Starting Work

**Always run `git pull`** before making any changes.

## MANDATORY: When Working on Skills

When adding/editing/removing a skill, update ALL of these:

1. `skills/<name>/SKILL.md` — Main skill entry point
2. `skills/<name>/references/*.md` — Sub-files if applicable
3. `.claude-plugin/marketplace.json` — Add/update plugin entry
4. `README.md` — Update skills table

**Do not skip any of these.** All must stay in sync.

## Agent Skills Specification

Skills follow the [Agent Skills spec](https://agentskills.io/specification.md).

### Required Frontmatter

```yaml
---
name: skill-name
description: What this skill does and when to use it. Include trigger phrases.
license: MIT
---
```

### Frontmatter Field Constraints

| Field         | Required | Constraints                                                    |
|---------------|----------|----------------------------------------------------------------|
| `name`        | Yes      | 1-64 chars, lowercase `a-z`, numbers, hyphens. Must match dir. |
| `description` | Yes      | 1-1024 chars. Describe what it does and when to use it.        |
| `license`     | No       | License name (default: MIT)                                    |
| `metadata`    | No       | Key-value pairs (author, version, etc.)                        |

### Name Field Rules

- Lowercase letters, numbers, and hyphens only
- Cannot start or end with hyphen
- No consecutive hyphens (`--`)
- Must match parent directory name exactly

**Valid**: `csk-sdk`, `lisa-core`, `device-config`
**Invalid**: `CSK-SDK`, `-lisa`, `lisa--core`

### Skill Directory Structure

```
skills/skill-name/
├── SKILL.md        # Required — main instructions (<500 lines)
├── references/     # Optional — detailed docs loaded on demand
├── scripts/        # Optional — executable code
└── assets/         # Optional — templates, data files
```

## Skill Design Pattern

Skills use progressive loading — main `SKILL.md` is small (~300 tokens), references sub-files that users load based on context. Keeps context usage minimal.

**DO NOT** load all reference files at once. Load only what's relevant to the current task.

## Writing Style Guidelines

- Keep `SKILL.md` under 500 lines (move details to `references/`)
- Use H2 (`##`) for main sections, H3 (`###`) for subsections
- Short paragraphs (2-4 sentences max)
- Bold (`**text**`) for key terms, code blocks for examples
- Direct and instructional tone
- Clarity over cleverness, specific over vague

### Description Field Best Practices

The `description` is critical for skill discovery. Include:

1. What the skill does
2. When to use it (trigger phrases)
3. Related skills for scope boundaries

```yaml
description: When the user is working with LS SDK development. Use when the user mentions "LS", "firmware", "voice chip". For hardware config, see device-config.
```

## Git Workflow

### Branch Naming

- New skills: `feature/skill-name`
- Improvements: `fix/skill-name-description`
- Documentation: `docs/description`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add skill-name skill`
- `fix: improve clarity in skill-name`
- `docs: update README`

### Pull Request Checklist

- [ ] `name` matches directory name exactly
- [ ] `name` follows naming rules (lowercase, hyphens, no `--`)
- [ ] `description` is 1-1024 chars with trigger phrases
- [ ] `SKILL.md` is under 500 lines
- [ ] `.claude-plugin/marketplace.json` updated
- [ ] `README.md` skills table updated
- [ ] No sensitive data or credentials
