---
name: mr-pr-quality-gate
description: >
  MR/PR 质量门禁：准备提交时检查范围、目标分支同步、敏感信息和提交历史；
  处理已有 GitLab MR / GitHub PR 的 AI review 时，逐条核查反馈、修复或解释，
  在原讨论回复并解决主题。
license: MIT
---

# MR/PR 质量门禁

先确定用户要求的路径，按需读取对应流程：

- **准备、检查或提交 MR/PR**：读取 [提交门禁](references/submission.md)。完成条件是范围、同步、敏感信息与提交历史逐项验证；任何未通过项都如实报告。
- **处理已有 MR/PR 的 AI review**：读取 [讨论处理流程](references/ai-review.md)。完成条件是每条目标讨论都有判断、证据与回复，且可解决的主题已核实为 resolved；未完成项单列说明。

若请求同时涉及两项，分别执行并分别报告结论；AI 评论的处理结果不能替代提交门禁，提交门禁也不能替代逐条处理评论。
