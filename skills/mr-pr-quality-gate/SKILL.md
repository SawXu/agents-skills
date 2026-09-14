---
name: mr-pr-quality-gate
description: >
  Use when preparing, reviewing, or submitting a GitLab MR or GitHub PR, including
  requests to check commit history, inspect a diff, redact sensitive data, or
  decide whether a change is ready for review.
license: MIT
---

# MR/PR 质量门禁

把 MR/PR 当作一个可审阅、可复现、可安全发布的变更单元。完成前必须逐项通过下面的门禁；任何一项无法验证，都标记为“未通过”，不要宣称已准备好提交。

## 1. 先确定范围

```bash
git status --short --branch
git diff --stat
git diff --check
```

确认目标分支、变更基线和工作区状态。只包含本任务需要的文件；无关改动应移除或明确说明。

### 目标分支同步门禁

源分支必须包含目标分支的全部最新提交，落后提交数必须为 0。先确认当前 `HEAD` 是待提交的源分支，再从目标仓库获取目标分支；跨仓库 MR/PR 应使用目标仓库的 remote。以下以 `origin/main` 为例，执行时替换为实际目标：

```bash
git fetch origin refs/heads/main
target_sha=$(git rev-parse FETCH_HEAD)
git merge-base --is-ancestor "$target_sha" HEAD
git rev-list --left-right --count "$target_sha"...HEAD
```

只有 fetch 成功、祖先检查退出码为 0，且计数结果左侧（behind）为 0 时才通过；右侧为源分支的 ahead 数量。不能只比较提交总数、提交时间或源分支自身的 upstream，也不能以“无合并冲突”代替此检查。获取失败或历史不完整导致无法判断时，标记为“未通过”。

若源分支落后，先按仓库约定将目标分支合入，或在符合下文历史改写约束时 rebase 到目标分支，解决冲突后重新检查。推送或创建、更新 MR/PR 前须再次 fetch 并检查，确保目标分支在审查期间新增的提交也已包含。

## 2. 敏感信息门禁

对提交范围和工作树同时检查：

- 密钥、Token、密码、私钥、证书、Cookie、Authorization、内部 URL、个人信息、设备序列号和生产数据；
- `.env`、构建产物、日志、转储、临时文件和本地配置；
- 示例或测试中的真实凭据，即使已失效也优先替换为明显的占位符。

使用仓库已有的 secret scanner；若没有，至少检查：

```bash
git diff --unified=0 <base>...HEAD
git grep -n -I -E '(BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|AKIA[0-9A-Z]{16}|Bearer [A-Za-z0-9._-]+|password[[:space:]]*[:=]|token[[:space:]]*[:=])' <base>...HEAD -- . ':!*.lock' || true
```

发现敏感信息时，先从 Git 历史中移除并轮换凭据，再继续；仅删除当前文件不算通过。报告扫描工具、范围和结论。

## 3. Commit hygiene 门禁

提交历史应表达清晰的逻辑单元：

```bash
git log --oneline --decorate <base>..HEAD
git diff --name-status <base>...HEAD
git log --format='%H %s' --reverse <base>..HEAD
```

目标状态：

- 每个 commit 可独立理解，标题准确，正文说明原因和验证方式；
- 同一文件的修改围绕一个逻辑变更组织，而不是“改一次、补一次、再修一次”；
- 没有调试提交、无意义格式提交、临时回滚再重做、自动生成的大噪声；
- 相关提交应合并或 squash，使审阅者看到最小且连贯的提交序列；
- 不改写共享分支历史；若需要 rebase/squash，先确认分支是个人 MR 分支。

“同一文件在多个 commit 出现”是审查信号，不是绝对错误：若确实是独立阶段且每个阶段有明确价值，可保留并在结论中解释。否则在提交前整理历史。

### 子模块提交顺序

如果当前仓库包含子模块改动，必须先完成子模块仓库的提交和推送，再提交或更新当前仓库中的子模块指针，最后推送当前仓库。推送前逐项验证：

1. 子模块工作区干净，目标 commit 已存在于子模块远端可供 CI fetch 的分支或 tag；
2. 当前仓库记录的子模块 SHA 与已推送的子模块 commit 完全一致；
3. 只有确认子模块远端可访问后，才推送当前仓库引用该 SHA 的 commit。

不得先推送外层仓库再补推子模块，否则 CI 可能因 `not our ref` 或无法 fetch 子模块 commit 而失败。

## 4. 提交前结论

本 skill 只负责 MR/PR 的**提交范围、目标分支同步、敏感信息和提交历史**约束，不负责代码正确性、测试充分性、错误处理、边界条件、兼容性、文档同步或构建验证；这些内容交由其他专门的 review/test skill 处理。

输出以下结构：

- **范围**：基线、目标分支、变更文件；
- **目标分支同步**：目标 remote/分支、fetch 后的目标 SHA、源分支 HEAD SHA、ahead/behind 数量、祖先检查结果及同步动作；
- **敏感信息**：扫描方式、结果、是否需要轮换凭据；
- **提交历史**：commit 数量、是否存在重复修改/临时提交、整理动作；
- **未覆盖项**：明确说明本 skill 未检查代码质量、测试和构建结果；
- **结论**：只有范围、目标分支同步、敏感信息和提交历史门禁均已验证通过，才能写“满足 MR/PR 提交规范”；不得据此宣称代码或测试已通过。

创建 GitLab MR 时优先使用项目约定的 `git push` merge-request options；GitHub PR 使用 `gh`。除非用户明确授权，不要自动 push、创建 MR/PR 或删除分支。
