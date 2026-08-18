# 需求分析质量门禁流程

本项目使用 OpenCode 协作模式，不调用远程模型 API。模型负责生成和修复测试点内容，本地 Python 程序负责质量判定和正式结果生成。

## 固定流程

1. 读取用户指定的需求文档和冻结的 `prompt.md`。
2. 根据需求文档和 `prompt.md` 生成严格 JSON，并保存为项目根目录的 `analysis.json`。
3. 执行本地质量门禁：

   ```powershell
   python -m analysis_quality_gate.pipeline process analysis.json --output-dir output
   ```

4. 读取 `output/reports/validation.json`。
5. 如果 `passed` 为 `false`，读取错误报告并修复 `analysis.json`；不得修改 `prompt.md`，不得直接修改正式 Markdown。
6. 修复后重新执行质量门禁，最多修复 2 次。
7. 只有 `passed` 为 `true` 时，才允许使用 `output/需求分析结果.md`。
8. 如果连续 2 次修复仍失败，停止流程并报告错误，不得强行生成正式结果。

## 强制约束

- `prompt.md` 是冻结文件，除非用户明确要求，不得修改。
- 不使用 `.env`、API Key、`model_client.py` 或远程模型调用。
- 不绕过 `analysis_quality_gate` 直接生成或修改正式结果。
- `analysis.json` 是模型中间结果；`output/需求分析结果.md` 是质量门禁通过后的正式结果。
- 质量判定以本地校验程序为准，不以模型自检结论为准。
- 待补充测试点不得进入后续测试用例生成流程。
- 实际测试用例执行由人工完成；本项目不自动执行测试用例。
- 测试用例 JSON 校验失败时，读取 `test_case_generation/reports/validation.json`，修复 `test_case_generation/test_cases.json` 后重新校验。

## 文件职责

- `prompt.md`：冻结的需求分析提示词。
- `analysis.json`：模型生成的中间 JSON。
- `analysis_quality_gate/`：结构校验、业务校验和 Markdown 渲染。
- `output/reports/validation.json`：质量门禁报告。
- `output/需求分析结果.md`：通过质量门禁后的正式结果。
