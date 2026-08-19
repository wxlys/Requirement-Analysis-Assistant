# 需求分析质量门禁流程

本项目使用 OpenCode 协作模式，不调用远程模型 API。模型负责生成和修复测试点内容，本地 Python 程序负责质量判定和正式结果生成。

每个任务在独立工作目录中执行，互不影响。任务工作目录由命令参数指定为**绝对路径**（形如 `/data/workspaces/<任务ID>`），下文用 `{workspace}` 表示。

## 固定流程

1. 读取用户指定的需求文档（位于 `{workspace}/`）和冻结的 `prompt.md`。
2. 根据需求文档和 `prompt.md` 生成严格 JSON，保存为 `{workspace}/analysis.json`。
3. 执行本地质量门禁：

   ```powershell
   python -m analysis_quality_gate.pipeline process {workspace}/analysis.json --output-dir {workspace}/output
   ```

4. 读取 `{workspace}/output/reports/validation.json`。
5. 如果 `passed` 为 `false`，读取错误报告并修复 `{workspace}/analysis.json`；不得修改 `prompt.md`，不得直接修改正式 Markdown。
6. 修复后重新执行质量门禁，最多修复 2 次。
7. 只有 `passed` 为 `true` 时，才允许使用 `{workspace}/output/需求分析结果.md`。
8. 如果连续 2 次修复仍失败，停止流程并报告错误，不得强行生成正式结果。

## 强制约束

- `prompt.md` 是冻结文件，除非用户明确要求，不得修改。
- 不使用 `.env`、API Key、`model_client.py` 或远程模型调用。
- 不绕过 `analysis_quality_gate` 直接生成或修改正式结果。
- `{workspace}/analysis.json` 是模型中间结果；`{workspace}/output/需求分析结果.md` 是质量门禁通过后的正式结果。
- 质量判定以本地校验程序为准，不以模型自检结论为准。
- 待补充测试点不得进入后续测试用例生成流程。
- 实际测试用例执行由人工完成；本项目不自动执行测试用例。
- 测试用例 JSON 校验失败时，读取 `{workspace}/test_case_generation/reports/validation.json`，修复 `{workspace}/test_case_generation/test_cases.json` 后重新校验。
- 只读写 `{workspace}/` 内的中间产物，不读写其它任务工作目录，不向项目根目录写入 `analysis.json`、`output/` 等中间产物。
- 读取文件请使用 bash 的 `cat` 命令，不要使用 opencode 的 read 工具（read 工具对项目目录外的路径（如 `/data` 卷）可能挂起）。

## 文件职责

- `prompt.md`：冻结的需求分析提示词。
- `{workspace}/analysis.json`：模型生成的中间 JSON。
- `analysis_quality_gate/`：结构校验、业务校验和 Markdown 渲染。
- `{workspace}/output/reports/validation.json`：质量门禁报告。
- `{workspace}/output/需求分析结果.md`：通过质量门禁后的正式结果。
- `{workspace}/test_case_generation/test_cases.json`：测试用例权威数据源（由模型生成，经本地校验）。
- `{workspace}/test_case_generation/test_cases.md`：渲染后的人读测试用例。
