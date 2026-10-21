---
name: pr-ci-review-fix
disable-model-invocation: true
description: 用 glab/gh 检查 CI 中的 AI review 意见，修复有效问题，对无须修改的意见回复原因；修复后整理 commits 并更新 PR/MR。
license: MIT
---

# 处理 CI 中的 AI Review 问题

按 [讨论处理](references/ai-review.md) 用 `glab` / `gh` 检查 CI 中的 AI review：有问题修复并验证，无须修改则在原线程回复原因和证据。

修复后执行 [pr-commits-tidy](../pr-commits-tidy/SKILL.md)，整理提交并推送更新 PR/MR，再回复最终提交和验证结果、Resolve 已处理的讨论。用户仅要求检查或本地修复时，遵循其限制。合并由用户在平台执行。
