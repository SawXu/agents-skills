# 补充任务上下文

仅在问题需要详情之外的证据时读取本文件。沿用主流程已确认的 `SERVER`、`WORKSPACE_ID`、`ISSUE_ID` 和只读边界；执行所选分支前，先查看对应命令的 `--help`，按本机能力调整参数。

## 评论讨论

先看根评论摘要，再根据问题选择具体线程，避免默认拉取全部评论。

```bash
multica issue comment list --help
multica --server-url "$SERVER" --workspace-id "$WORKSPACE_ID" issue comment list "$ISSUE_ID" --roots-only --summary --compact --output json
```

需要某条讨论的内容时，用返回的评论 ID 读取线程：

```bash
COMMENT_ID='<返回的评论 ID>'
multica --server-url "$SERVER" --workspace-id "$WORKSPACE_ID" issue comment list "$ISSUE_ID" --thread "$COMMENT_ID" --tail 20 --compact --output json
```

**完成条件**：已取得问题涉及的讨论证据；记录哪些线程已读，以及是否仅为摘要或最近 20 条。需要更早内容时，按当前帮助支持的读取选项扩展范围。

## 子任务

```bash
multica issue children --help
multica --server-url "$SERVER" --workspace-id "$WORKSPACE_ID" issue children "$ISSUE_ID" --output json
```

**完成条件**：已取得子任务关系及回答所需字段；需要某个子任务正文时，使用其完整 UUID 返回主流程步骤 3 的 `get` 读取。

## 执行记录或活动历史

根据问题只选择执行记录、活动或两者，不默认全部执行。

```bash
# 执行记录
multica issue runs --help
multica --server-url "$SERVER" --workspace-id "$WORKSPACE_ID" issue runs "$ISSUE_ID" --output json

# 近期活动
multica issue timeline --help
multica --server-url "$SERVER" --workspace-id "$WORKSPACE_ID" issue timeline "$ISSUE_ID" --activity-only --tail 20 --output json
```

**完成条件**：已取得所需执行记录或活动证据，并记录 `activity-only`、最近 20 条等具体范围。若问题需要进一步执行日志，先通过当前帮助确认可用的只读入口；入口不支持时按主流程报告未覆盖部分。

完成所选分支后返回主流程步骤 4 交付。
