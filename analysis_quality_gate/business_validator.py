from __future__ import annotations

import re
from typing import Any

from .validation import ValidationIssue

FORBIDDEN_EXPECTED_TERMS = (
    "或重定向",
    "或返回",
    "或失败",
    "二选一",
    "视情况",
    "按配置",
    "应该",
    "结果正常",
    "具体方式未定义",
    "处理结果未定义",
)
UNDEFINED_TERMS = ("【缺失】", "未定义", "待补充", "具体规则缺失")


def validate_business_rules(document: dict[str, Any]) -> list[ValidationIssue]:
    test_points = document["testPoints"]
    gaps = document["gaps"]
    test_point_map = {item["id"]: item for item in test_points}
    gap_map = {item["id"]: item for item in gaps}
    issues: list[ValidationIssue] = []

    for test_point in test_points:
        issues.extend(_validate_test_point(test_point, test_point_map, gap_map))
    for gap in gaps:
        issues.extend(_validate_gap(gap, test_point_map))
    issues.extend(_validate_requirement_ids(test_points))
    issues.extend(_validate_merged_rules(test_points))
    return issues


def _validate_test_point(
    test_point: dict[str, Any],
    test_point_map: dict[str, dict[str, Any]],
    gap_map: dict[str, dict[str, Any]],
) -> list[ValidationIssue]:
    point_id = test_point["id"]
    status = test_point["status"]
    gap_ids = set(test_point["gapIds"])
    issues: list[ValidationIssue] = []

    for gap_id in gap_ids:
        if gap_id not in gap_map:
            issues.append(ValidationIssue("UNKNOWN_GAP_REFERENCE", f"引用不存在的 GAP: {gap_id}", test_point_id=point_id, gap_id=gap_id))
        elif point_id not in gap_map[gap_id]["affectedTestPointIds"]:
            issues.append(ValidationIssue("GAP_REVERSE_REFERENCE", f"GAP 未反向引用测试点: {gap_id}", test_point_id=point_id, gap_id=gap_id))

    if status == "可直接生成用例" and gap_ids:
        issues.append(ValidationIssue("STATUS_GAP_CONFLICT", "可直接生成用例的测试点不能关联 GAP", test_point_id=point_id))
    if status in {"待补充需求", "暂不可测试"} and not gap_ids:
        issues.append(ValidationIssue("MISSING_GAP_REFERENCE", "待补充测试点必须关联至少一个 GAP", test_point_id=point_id))

    expected_text = "；".join(test_point["expected"])
    if any(term in expected_text for term in FORBIDDEN_EXPECTED_TERMS):
        issues.append(ValidationIssue("UNCERTAIN_EXPECTED", "预期结果包含不确定表达", test_point_id=point_id))
    if status == "可直接生成用例":
        checked_fields = ["sourceSummary", "preconditions", "testData", "trigger", "expected", "postconditions"]
        for field in checked_fields:
            values = test_point[field] if isinstance(test_point[field], list) else [test_point[field]]
            if any(term in str(value) for value in values for term in UNDEFINED_TERMS):
                issues.append(ValidationIssue("UNDEFINED_DIRECT_POINT", f"可执行测试点的 {field} 包含未定义内容", test_point_id=point_id))
    return issues


def _validate_gap(gap: dict[str, Any], test_point_map: dict[str, dict[str, Any]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    gap_id = gap["id"]
    affected = set(gap["affectedTestPointIds"])
    for point_id in affected:
        if point_id not in test_point_map:
            issues.append(ValidationIssue("UNKNOWN_TEST_POINT_REFERENCE", f"GAP 引用不存在的测试点: {point_id}", gap_id=gap_id, test_point_id=point_id))
        elif gap_id not in test_point_map[point_id]["gapIds"]:
            issues.append(ValidationIssue("TEST_POINT_REVERSE_REFERENCE", f"测试点未反向引用 GAP: {gap_id}", gap_id=gap_id, test_point_id=point_id))
        elif test_point_map[point_id]["status"] == "可直接生成用例":
            issues.append(ValidationIssue("GAP_STATUS_CONFLICT", "GAP 影响的测试点不能标记为可直接生成用例", gap_id=gap_id, test_point_id=point_id))
    return issues


def _validate_requirement_ids(test_points: list[dict[str, Any]]) -> list[ValidationIssue]:
    # Multiple test points may intentionally share one requirement ID. This check
    # only rejects an obviously unstable requirement ID sequence within one module.
    issues: list[ValidationIssue] = []
    by_requirement: dict[str, list[str]] = {}
    for point in test_points:
        by_requirement.setdefault(point["requirementId"], []).append(point["id"])
    for requirement_id, point_ids in by_requirement.items():
        if len(point_ids) > 1 and len(set(point_ids)) != len(point_ids):
            issues.append(ValidationIssue("DUPLICATE_TEST_POINT", f"需求 {requirement_id} 存在重复测试点"))
    return issues


def _validate_merged_rules(test_points: list[dict[str, Any]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for point in test_points:
        text = " ".join([point["name"], *point["testData"], *point["expected"]])
        point_id = point["id"]
        if _contains_pair(text, "禁用", "锁定"):
            issues.append(ValidationIssue("MERGED_ACCOUNT_STATES", "禁用账号和锁定账号必须拆分", test_point_id=point_id))
        if _contains_pair(text, "网络异常", "系统异常"):
            issues.append(ValidationIssue("MERGED_EXCEPTIONS", "网络异常和系统异常必须拆分", test_point_id=point_id))
        if _contains_pair(text, "成功登录", "失败登录"):
            issues.append(ValidationIssue("MERGED_OUTCOMES", "成功登录和失败登录必须拆分", test_point_id=point_id))
        fields = re.findall(r"`([A-Za-z][A-Za-z0-9_]*)`", text)
        if point["type"] == "反向" and point["name"].find("类型非法") >= 0 and len(set(fields)) > 1:
            issues.append(ValidationIssue("MERGED_INPUT_FIELDS", "不同输入字段的非法类型必须拆分", test_point_id=point_id))
    return issues


def _contains_pair(text: str, first: str, second: str) -> bool:
    return first in text and second in text
