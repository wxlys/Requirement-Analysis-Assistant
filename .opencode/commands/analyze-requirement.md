---
description: 按本项目固定流程生成、校验并修复需求分析测试点
agent: build
---

按项目根目录 `AGENTS.md` 中的固定流程执行需求分析。用户指定的需求文档为：`$ARGUMENTS`。

必须遵守：

1. 读取需求文档和冻结的 `prompt.md`。
2. 生成严格 JSON，保存到 `analysis.json`。
3. 执行：

   ```powershell
   python -m analysis_quality_gate.pipeline process analysis.json --output-dir output
   ```

4. 读取 `output/reports/validation.json`。
5. `passed=false` 时，只根据错误报告修复 `analysis.json`，不得修改 `prompt.md`，然后重新执行质量门禁。
6. 最多修复 2 次；仍失败时停止并报告错误。
7. `passed=true` 后，报告正式结果路径 `output/需求分析结果.md`。

不要调用远程 API，不要读取或使用 `.env`，不要绕过本地质量门禁。
