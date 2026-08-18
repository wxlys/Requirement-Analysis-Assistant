from __future__ import annotations

import argparse
import json
from pathlib import Path


def render(document: dict) -> str:
    cases = document["testCases"]
    categories: dict[str, int] = {}
    for case in cases:
        categories[case["category"]] = categories.get(case["category"], 0) + 1

    lines = ["# 测试用例清单", ""]
    lines.append(f"- 用例总数：{len(cases)}")
    if categories:
        lines.append(f"- 类别分布：{'、'.join(f'{key} {value}' for key, value in sorted(categories.items()))}")
    lines.append("")

    for case in cases:
        lines.append(f"## {case['id']} {case['name']}")
        lines.append("")
        lines.append(f"- 类别：{case['category']} | 优先级：{case['priority']} | 状态：{case['status']}")
        lines.append(f"- 覆盖测试点：{'、'.join(case['testPointIds'])}")
        lines.append(f"- 需求编号：{'、'.join(case['requirementIds'])}")
        for source in case.get("requirementSources", []):
            lines.append(f"- 需求来源（{source.get('section', '')}）：{_escape(source.get('summary', ''))}")
        lines.append("")
        _block(lines, "前置条件", case.get("preconditions", []))
        _block(lines, "测试数据", case.get("testData", []))
        _block(lines, "测试步骤", case.get("steps", []))
        _block(lines, "预期结果", case.get("expectedResults", []))
        _block(lines, "后置条件", case.get("postconditions", []))
        if case.get("assumptionIds"):
            lines.append(f"- 假设项：{'、'.join(case['assumptionIds'])}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _block(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        lines.append(f"**{title}：** 无")
        lines.append("")
        return
    lines.append(f"**{title}：**")
    for value in values:
        lines.append(f"1. {_escape(value)}")
    lines.append("")


def _escape(value: str) -> str:
    return value.replace("\n", "<br>")


def main() -> int:
    parser = argparse.ArgumentParser(description="将测试用例 JSON 渲染为人读的 Markdown")
    parser.add_argument("input", type=Path, help="test_cases.json 路径")
    parser.add_argument("--output", type=Path, required=True, help="输出 Markdown 路径")
    args = parser.parse_args()

    document = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(document), encoding="utf-8")
    print(f"已渲染 {len(document.get('testCases', []))} 条用例到 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())