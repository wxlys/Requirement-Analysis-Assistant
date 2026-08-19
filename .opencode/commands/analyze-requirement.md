---
description: 按本项目固定流程生成、校验并修复需求分析测试点
agent: build
---

按项目根目录 `AGENTS.md` 中的固定流程执行需求分析。`$ARGUMENTS` 格式为：`<需求文档文件名> <工作目录绝对路径>`，需求文档位于该工作目录下，该绝对路径即 `{workspace}`。

必须遵守：

1. 读取文件请使用 bash 的 `cat` 命令，不要使用 opencode 的 read 工具（read 工具对项目目录外的路径可能挂起）。
2. 读取 `{workspace}/` 下的需求文档，以及项目根目录冻结的 `prompt.md`。
3. 生成严格 JSON，保存到 `{workspace}/analysis.json`。
4. 执行：

   ```powershell
   python -m analysis_quality_gate.pipeline process {workspace}/analysis.json --output-dir {workspace}/output
   ```

5. 读取 `{workspace}/output/reports/validation.json`。
6. `passed=false` 时，只根据错误报告修复 `{workspace}/analysis.json`，不得修改 `prompt.md`，然后重新执行质量门禁。
7. 最多修复 2 次；仍失败时停止并报告错误。
8. `passed=true` 后，报告正式结果路径 `{workspace}/output/需求分析结果.md`。

不要调用远程 API，不要读取或使用 `.env`，不要绕过本地质量门禁。