---
description: 根据通过质量门禁的测试点生成并校验测试用例
agent: build
---

按项目根目录 `AGENTS.md` 执行测试用例生成流程。`$ARGUMENTS` 为工作目录绝对路径（即 `{workspace}`，如 `/data/workspaces/<任务ID>`）。

1. 读取文件请使用 bash 的 `cat` 命令，不要使用 opencode 的 read 工具（read 工具对项目目录外的路径可能挂起）。
2. 读取 `{workspace}/output/validated/analysis.json`。
3. 只使用状态为“可直接生成用例”的测试点。
4. 读取 `test_case_generation/prompt.md`，生成 `{workspace}/test_case_generation/test_cases.json`。
5. 执行：

   ```powershell
   python test_case_generation\validate_test_cases.py {workspace}/output/validated/analysis.json {workspace}/test_case_generation/test_cases.json --report {workspace}/test_case_generation/reports/validation.json
   ```

6. 如果校验失败，读取 `{workspace}/test_case_generation/reports/validation.json`，结合 `test_case_generation/repair_prompt.md` 修复 `{workspace}/test_case_generation/test_cases.json`，然后重新校验。
7. 测试用例质量校验最多修复 2 次；仍失败时停止并报告错误。
8. 实际测试用例执行由人工完成，不自动执行测试。