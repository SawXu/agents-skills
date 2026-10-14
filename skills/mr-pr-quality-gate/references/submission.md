# 提交门禁

终点是四项均已验证的报告。任一项无法验证，该项记为未通过。

## 1. 范围

```bash
git status --short --branch
git diff --stat
git diff --check
```

确定目标分支、变更基线和工作区状态。只纳入本任务需要的文件。

完成：目标分支、基线、变更文件都已确定；无关改动已处理或已说明。

## 2. 同步

源分支包含目标分支的全部最新提交。`HEAD` 须是待提交源分支。跨仓库时从目标仓库的 remote 获取目标分支。把 `origin/main` 换成实际目标：

```bash
git fetch origin refs/heads/main
target_sha=$(git rev-parse FETCH_HEAD)
git merge-base --is-ancestor "$target_sha" HEAD
git rev-list --left-right --count "$target_sha"...HEAD
```

通过条件同时成立：fetch 成功、历史完整、祖先检查退出码为 0、左侧 behind 为 0。右侧是 ahead。提交总数、时间、upstream 或“无冲突”都不能代替这几项。

落后时，仅在以下条件全部成立时执行 `git rebase "$target_sha"`：工作区和暂存区干净；当前分支是未被他人共用的个人分支；若已推送，后续推送不会覆盖他人提交。任一条件无法确认就停，把同步方式交给用户。冲突时列出冲突文件，并给出 continue 或 abort；保留全部提交和改动。rebase 后重跑祖先检查。推送或创建、更新 MR/PR 之前再 fetch 一次；目标又前进就重复本段。远端更新留到用户同意对应推送方式之后。

完成：当前目标 SHA 是 HEAD 的祖先，且 behind 为 0。

## 3. 敏感信息

扫描提交范围和工作树中的密钥、Token、密码、私钥、证书、Cookie、Authorization、内部 URL、个人信息、设备序列号、生产数据，以及 `.env`、产物、日志、转储和本地配置。示例和测试里的真实凭据换成占位符。

优先用仓库已有的 secret scanner。没有的话，检查 `git diff --unified=0 <base>...HEAD`、暂存区与未跟踪文件，并搜索常见密钥格式、Bearer 和 password/token 赋值。

发现凭据时，从历史中移除并轮换该凭据，然后重新扫描。只删当前文件不算通过。

完成：报告写明扫描工具、范围和结果；有凭据时写明移除范围与轮换状态。

## 4. 提交历史

```bash
git log --oneline --decorate <base>..HEAD
git diff --name-status <base>...HEAD
git log --format='%H %s' --reverse <base>..HEAD
```

每个 commit 可独立理解：标题准确，正文写原因和验证方式。把调试提交、临时回滚、无意义格式提交和生成噪声收成最小且连贯的序列。同一文件多次出现时说明各次的独立价值，否则整理历史。改写历史只在个人分支、且确认不会改写他人提交时进行。

有子模块时，先提交并推送子模块，确认该 SHA 能被 CI 从子模块远端 fetch，且外层记录的 SHA 与之相同，再提交、推送外层。

完成：历史可审阅；每个被引用的子模块 SHA 已在远端可访问，并与外层记录一致。

## 5. 报告

按四项写结果：

- 范围：基线、目标分支、文件
- 同步：remote、目标 SHA、HEAD SHA、ahead/behind、祖先检查、已做动作
- 敏感信息：方式、结果、轮换
- 提交历史：数量、重复或临时提交、整理动作

四项都通过才写“满足 MR/PR 提交规范”。代码质量、测试和构建只在另外验证后写入。

推送、创建或更新 MR/PR、删除分支是用户另行授权的动作。创建 GitLab MR 时用项目约定的 git push merge-request options；创建 GitHub PR 用 `gh`。这些选项只创建或更新，不携带合并或自动合并参数。
