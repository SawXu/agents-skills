---
name: mr-pr-quality-gate
disable-model-invocation: true
description: 检查 MR/PR 能否提交，或逐条处理其中的 AI review；合并由用户在平台执行。
license: MIT
---

# MR/PR 质量门禁

先确定路径，只读取该路径的流程：

- **提交**：准备、检查或提交 MR/PR 时读取 [提交门禁](references/submission.md)。终点是范围、同步、敏感信息、提交历史四项都已验证的报告。
- **讨论**：处理已有 MR/PR 的 AI review 时读取 [讨论处理](references/ai-review.md)。终点是每条目标讨论都有判断、证据和原线程回复，且可解决的主题已核实为 resolved。

两项同时出现时分别执行、分别报告。讨论处理不能代替提交门禁，提交门禁也不能代替逐条处理评论。

**合并权在用户。** 任一路径都停在可核对的报告。不调用合并 API，不点 Merge，也不开启“流水线通过后自动合并”。同一请求里即使写了合并，也只交付报告，由用户在平台合并。
