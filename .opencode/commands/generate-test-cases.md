---
description: 根据通过质量门禁的测试点生成并校验测试用例
agent: build
---

按项目根目录 `AGENTS.md` 执行测试用例生成流程。

1. 读取 `output/validated/analysis.json`。
2. 只使用状态为“可直接生成用例”的测试点。
3. 读取 `test_case_generation/prompt.md`，生成 `test_case_generation/test_cases.json`。
4. 执行：

   ```powershell
   python test_case_generation\validate_test_cases.py output\validated\analysis.json test_case_generation\test_cases.json
   ```

5. 如果校验失败，读取 `test_case_generation/reports/validation.json`，结合 `test_case_generation/repair_prompt.md` 修复 `test_cases.json`，然后重新校验。
6. 测试用例质量校验最多修复 2 次；仍失败时停止并报告错误。
7. 实际测试用例执行由人工完成，不自动执行测试。
