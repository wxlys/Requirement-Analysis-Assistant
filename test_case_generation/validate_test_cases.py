from __future__ import annotations

import json
import re
import sys
import argparse
from pathlib import Path


REQUIRED_CASE_FIELDS = {
    "id",
    "testPointIds",
    "requirementIds",
    "requirementSources",
    "category",
    "name",
    "preconditions",
    "testData",
    "steps",
    "expectedResults",
    "postconditions",
    "priority",
    "status",
    "assumptionIds",
}
CATEGORIES = {"正向", "异常", "边界", "场景"}
STATUSES = {"可执行", "待确认"}
PRIORITIES = {"P0", "P1", "P2", "P3"}


def validate(test_points_path: Path, cases_path: Path) -> tuple[list[str], dict]:
    analysis = json.loads(test_points_path.read_text(encoding="utf-8"))
    cases_document = json.loads(cases_path.read_text(encoding="utf-8"))
    executable = {
        point["id"] for point in analysis["testPoints"] if point["status"] == "可直接生成用例"
    }
    cases = cases_document["testCases"]
    errors: list[str] = []
    ids = [case["id"] for case in cases]
    expected_ids = [f"UC-{index:03d}" for index in range(1, len(cases) + 1)]
    if ids != expected_ids:
        errors.append("用例编号不是从 UC-001 开始的连续编号")
    if len(ids) != len(set(ids)):
        errors.append("用例编号重复")

    referenced_points: set[str] = set()
    category_counts = {category: 0 for category in CATEGORIES}
    for case in cases:
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            errors.append(f"{case.get('id', '<unknown>')} 缺少字段: {sorted(missing)}")
        if not re.fullmatch(r"UC-\d{3}", case.get("id", "")):
            errors.append(f"用例编号格式错误: {case.get('id')}")
        if case.get("category") not in CATEGORIES:
            errors.append(f"用例类别非法: {case.get('id')}")
        else:
            category_counts[case["category"]] += 1
        if case.get("priority") not in PRIORITIES:
            errors.append(f"用例优先级非法: {case.get('id')}")
        if case.get("status") not in STATUSES:
            errors.append(f"用例状态非法: {case.get('id')}")
        if case.get("status") == "待确认" and not case.get("assumptionIds"):
            errors.append(f"待确认用例缺少 assumptionIds: {case.get('id')}")
        for point_id in case.get("testPointIds", []):
            referenced_points.add(point_id)
            if point_id not in executable:
                errors.append(f"用例引用了不可执行测试点: {case.get('id')} -> {point_id}")
        for field in ("preconditions", "testData", "steps", "expectedResults", "postconditions"):
            if not isinstance(case.get(field), list) or not all(isinstance(value, str) for value in case[field]):
                errors.append(f"{case.get('id')} 的 {field} 必须是字符串数组")

    for category, count in category_counts.items():
        if count == 0:
            errors.append(f"缺少用例类别: {category}")
    declared_counts = coverage_counts = cases_document.get("coverage", {}).get("categories", {})
    if declared_counts != category_counts:
        errors.append(f"类别数量自查不一致: 声明={declared_counts}, 实际={category_counts}")
    for point_id in sorted(executable - referenced_points):
        errors.append(f"可执行测试点未覆盖: {point_id}")

    coverage = cases_document.get("coverage", {})
    case_ids = set(ids)
    for row in coverage.get("requirements", []):
        for case_id in row.get("testCaseIds", []):
            if case_id not in case_ids:
                errors.append(f"覆盖表引用不存在的用例: {case_id}")
        for point_id in row.get("testPointIds", []):
            if point_id not in executable:
                errors.append(f"覆盖表引用不可执行测试点: {point_id}")
    if coverage.get("uncoveredItems"):
        errors.append(f"存在未覆盖项: {coverage['uncoveredItems']}")
    report = {
        "passed": not errors,
        "testPointCount": len(executable),
        "testCaseCount": len(cases),
        "categoryCounts": category_counts,
        "coveredTestPointIds": sorted(referenced_points),
        "uncoveredTestPointIds": sorted(executable - referenced_points),
        "errors": errors,
    }
    return errors, report


def main() -> int:
    parser = argparse.ArgumentParser(description="校验测试用例 JSON")
    parser.add_argument("analysis", type=Path)
    parser.add_argument("test_cases", type=Path)
    parser.add_argument("--report", type=Path, default=Path("test_case_generation/reports/validation.json"))
    args = parser.parse_args()

    errors, report = validate(args.analysis, args.test_cases)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if errors:
        print("TEST_CASE_VALIDATION_FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("TEST_CASE_VALIDATION_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
