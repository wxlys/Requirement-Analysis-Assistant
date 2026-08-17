from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .business_validator import validate_business_rules
from .structural_validator import validate_structure


def validate_document(document: Any) -> dict[str, Any]:
    structural_errors = validate_structure(document)
    if structural_errors:
        return {"passed": False, "stage": "structure", "errors": [item.to_dict() for item in structural_errors], "warnings": []}
    business_errors = validate_business_rules(document)
    return {
        "passed": not business_errors,
        "stage": "business" if business_errors else "complete",
        "data": document if not business_errors else None,
        "errors": [item.to_dict() for item in business_errors],
        "warnings": [],
    }


def render_markdown(document: dict[str, Any]) -> str:
    result = validate_document(document)
    if not result["passed"]:
        raise ValueError(json.dumps(result, ensure_ascii=False, indent=2))

    points = sorted(document["testPoints"], key=lambda item: item["status"] != "可直接生成用例")
    lines = [
        "## 原子化测试点清单",
        "",
        "| 测试点编号 | 需求编号 | 需求章节 | 需求原文摘要 | 功能模块 | 测试类型 | 测试点名称 | 优先级 | 前置条件 | 测试数据 | 触发条件 | 预期结果 | 后置条件 | 依据状态 | 测试点状态 | 备注 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for point in points:
        values = [
            point["id"],
            point["requirementId"],
            point["sourceSection"],
            point["sourceSummary"],
            point["module"],
            point["type"],
            point["name"],
            point["priority"],
            _join(point["preconditions"]),
            _join(point["testData"]),
            point["trigger"],
            _join(point["expected"]),
            _join(point["postconditions"]),
            point["evidenceStatus"],
            point["status"],
            point["remarks"],
        ]
        lines.append("| " + " | ".join(_escape(value) for value in values) + " |")

    lines.extend([
        "",
        "## 待补充需求清单",
        "",
        "| 问题编号 | 缺失内容 | 影响测试点 | 影响 | 建议补充定义 | 依据状态 |",
        "|---|---|---|---|---|---|",
    ])
    for gap in document["gaps"]:
        values = [
            gap["id"],
            gap["content"],
            _join(gap["affectedTestPointIds"]),
            gap["impact"],
            gap["suggestion"],
            gap["evidenceStatus"],
        ]
        lines.append("| " + " | ".join(_escape(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def process(input_path: Path, output_dir: Path) -> int:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    result = validate_document(raw)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw").mkdir(exist_ok=True)
    (output_dir / "reports").mkdir(exist_ok=True)
    (output_dir / "raw" / input_path.name).write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "reports" / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result["passed"]:
        (output_dir / "rejected").mkdir(exist_ok=True)
        return 1
    (output_dir / "validated").mkdir(exist_ok=True)
    (output_dir / "validated" / input_path.name).write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "需求分析结果.md").write_text(render_markdown(raw), encoding="utf-8")
    return 0


def _join(values: list[str]) -> str:
    return "；".join(values)


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate model-generated test-point analysis JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("input", type=Path)
    validate_parser.add_argument("--report", type=Path)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("input", type=Path)
    render_parser.add_argument("--output", type=Path, required=True)

    process_parser = subparsers.add_parser("process")
    process_parser.add_argument("input", type=Path)
    process_parser.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "validate":
        result = validate_document(json.loads(args.input.read_text(encoding="utf-8")))
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.report:
            args.report.write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0 if result["passed"] else 1
    if args.command == "render":
        document = json.loads(args.input.read_text(encoding="utf-8"))
        args.output.write_text(render_markdown(document), encoding="utf-8")
        return 0
    return process(args.input, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
