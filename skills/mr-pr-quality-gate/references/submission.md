# MR/PR 提交门禁

按以下步骤检查待提交变更。任何一项无法验证，标记为“未通过”，不宣称可以提交。

## 1. 确定范围与目标分支

```bash
git status --short --branch
git diff --stat
git diff --check
```

确认目标分支、变更基线和工作区状态；仅纳入本任务需要的文件。完成标准：目标分支、基线与变更文件均已确定，无关改动已处理或说明。

### 目标分支同步

源分支必须包含目标分支的全部最新提交。确认当前 `HEAD` 是待提交源分支，从目标仓库获取目标分支；跨仓库 MR/PR 使用目标仓库的 remote。以 `origin/main` 为例（替换为实际目标）：

```bash
git fetch origin refs/heads/main
target_sha=$(git rev-parse FETCH_HEAD)
git merge-base --is-ancestor "$target_sha" HEAD
git rev-list --left-right --count "$target_sha"...HEAD
```

fetch 成功、祖先检查退出码为 0、左侧 behind 为 0 才通过；右侧为 ahead。获取失败或历史不完整时标记“未通过”；提交总数、时间、upstream 或“无合并冲突”不能代替此检查。

若落后，先确认工作区和暂存区干净、当前分支是个人 MR/PR 分支且未被他人共用；已推送时还需确认后续推送不会覆盖他人提交。无法确认则停止，请用户决定同步方式；未经明确授权不强制推送。安全条件满足时自动执行 `git rebase "$target_sha"`。冲突时报告冲突文件及 continue/abort 选择，不跳过提交或丢弃改动。rebase 后重新核查祖先关系和 behind。推送或创建、更新 MR/PR 前再次 fetch 检查；目标前进则重复上述安全流程。完成标准：fetch 成功、当前目标 SHA 是 HEAD 祖先且 behind 为 0。

## 2. 敏感信息

检查提交范围与工作树中的密钥、Token、密码、私钥、证书、Cookie、Authorization、内部 URL、个人信息、设备序列号、生产数据，以及 `.env`、产物、日志、转储和本地配置。示例或测试中的真实凭据也应替换为占位符。

使用仓库已有 secret scanner；若没有，至少检查 `git diff --unified=0 <base>...HEAD`、未提交变更（含暂存区和未跟踪文件），并在变更文件和历史中搜索常见密钥格式、Bearer 凭据及 password/token 赋值。发现凭据时从历史中移除并轮换，再继续；仅删除当前文件不算通过。完成标准：报告扫描工具、范围、结果和轮换状态。

## 3. Commit hygiene

```bash
git log --oneline --decorate <base>..HEAD
git diff --name-status <base>...HEAD
git log --format='%H %s' --reverse <base>..HEAD
```

每个 commit 应可独立理解，标题准确，正文说明原因和验证方式；整理调试提交、临时回滚、无意义格式提交和生成噪声。相关改动组织为最小且连贯的序列。同一文件多次出现是审查信号，不是绝对错误；确属独立阶段则说明价值，否则整理历史。仅在个人分支且安全时 rebase/squash，不改写共享分支历史。

若有子模块改动，先提交并推送子模块，确认该 SHA 可被 CI 从子模块远端 fetch，且外层仓库记录的 SHA 完全一致，再提交、推送外层仓库。完成标准：历史可审阅，且被引用的子模块 SHA 已在远端可访问。

## 4. 结论

逐项报告范围（基线、目标分支、文件）、同步（remote/目标 SHA、HEAD SHA、ahead/behind、祖先检查及动作）、敏感信息（方式、结果、轮换）、提交历史（数量、重复/临时提交、整理动作）。仅上述各项均验证通过时写“满足 MR/PR 提交规范”；代码质量、测试和构建结果仅在另行验证后报告。创建 GitLab MR 时优先使用项目约定的 git push merge-request options；GitHub PR 使用 `gh`。除非用户明确授权，不自动 push、创建 MR/PR 或删除分支。
