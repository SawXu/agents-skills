---
name: pr-commits-tidy
description: 整理 PR/MR 的 commits：合并重复提交与同一目的的修补，rebase 目标分支后用 --force-with-lease 推送。
license: MIT
---

# 整理 PR/MR 提交

1. 确认源分支、目标分支和推送 remote，fetch 最新分支。
2. rebase 目标分支；冲突按双方意图解决，不确定时询问用户。
3. 整理 commits，合并重复提交和同一目的的修补，独立功能保留分开。
4. 用 `--force-with-lease` 推送。