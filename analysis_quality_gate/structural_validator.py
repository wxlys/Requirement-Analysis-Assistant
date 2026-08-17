from __future__ import annotations

import re
from typing import Any

from .validation import ValidationIssue

TEST_POINT_FIELDS = {
    "id",
    "requirementId",
    "sourceSection",
    "sourceSummary",
    "module",
    "type",
    "name",
    "priority",
    "preconditions",
    "testData",
    "trigger",
    "expected",
    "postconditions",
    "evidenceStatus",
    "status",
    "gapIds",
    "remarks",
}

GAP_FIELDS = {
    "id",
    "content",
    "affectedTestPointIds",
    "impact",
    "suggestion",
    "evidenceStatus",
}

EVIDENCE_STATUSES = {"原文明确", "原文推导", "需求缺失", "建议补充", "待核对"}
TEST_POINT_STATUSES = {"可直接生成用例", "待补充需求", "暂不可测试"}
PRIORITIES = {"P0", "P1", "P2"}
TEST_TYPES = {
    "正向",
    "反向",
    "边界",
    "状态转换",
    "权限",
    "安全",
    "并发",
    "性能",
    "兼容性",
    "异常恢复",
    "数据完整性",
}

ID_PATTERNS = {
    "test point": re.compile(r"^TP-[A-Za-z0-9_-]+-\d{3}$"),
    "requirement": re.compile(r"^REQ-[A-Za-z0-9_-]+-\d{3}$"),
    "gap": re.compile(r"^GAP-\d{3}$"),
}


def validate_structure(document: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not isinstance(document, dict):
        return [ValidationIssue("ROOT_TYPE", "顶层数据必须是 JSON 对象", "$")]

    expected_root = {"testPoints", "gaps"}
    actual_root = set(document)
    for field in expected_root - actual_root:
        issues.append(ValidationIssue("MISSING_FIELD", f"缺少顶层字段: {field}", f"$.{field}"))
    for field in actual_root - expected_root:
        issues.append(ValidationIssue("UNKNOWN_FIELD", f"不允许的顶层字段: {field}", f"$.{field}"))

    test_points = document.get("testPoints")
    gaps = document.get("gaps")
    if not isinstance(test_points, list):
        issues.append(ValidationIssue("FIELD_TYPE", "testPoints 必须是数组", "$.testPoints"))
    if not isinstance(gaps, list):
        issues.append(ValidationIssue("FIELD_TYPE", "gaps 必须是数组", "$.gaps"))
    if issues:
        return issues

    test_point_ids: set[str] = set()
    gap_ids: set[str] = set()
    for index, test_point in enumerate(test_points):
        path = f"$.testPoints[{index}]"
        issues.extend(_validate_test_point(test_point, path, test_point_ids))
    for index, gap in enumerate(gaps):
        path = f"$.gaps[{index}]"
        issues.extend(_validate_gap(gap, path, gap_ids))
    return issues


def _validate_object_fields(
    value: Any,
    required: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> bool:
    if not isinstance(value, dict):
        issues.append(ValidationIssue("ITEM_TYPE", "条目必须是 JSON 对象", path))
        return False
    actual = set(value)
    for field in required - actual:
        issues.append(ValidationIssue("MISSING_FIELD", f"缺少字段: {field}", f"{path}.{field}"))
    for field in actual - required:
        issues.append(ValidationIssue("UNKNOWN_FIELD", f"不允许的字段: {field}", f"{path}.{field}"))
    return True


def _validate_test_point(value: Any, path: str, ids: set[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not _validate_object_fields(value, TEST_POINT_FIELDS, path, issues):
        return issues

    _validate_string_fields(value, {"id", "requirementId", "sourceSection", "sourceSummary", "module", "name", "trigger", "remarks"}, path, issues)
    _validate_string_array_fields(value, {"preconditions", "testData", "expected", "postconditions", "gapIds"}, path, issues)
    _validate_enum(value, "type", TEST_TYPES, path, issues)
    _validate_enum(value, "priority", PRIORITIES, path, issues)
    _validate_enum(value, "evidenceStatus", EVIDENCE_STATUSES, path, issues)
    _validate_enum(value, "status", TEST_POINT_STATUSES, path, issues)
    _validate_id(value, "id", "test point", ids, path, issues)
    _validate_id(value, "requirementId", "requirement", None, path, issues)
    return issues


def _validate_gap(value: Any, path: str, ids: set[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not _validate_object_fields(value, GAP_FIELDS, path, issues):
        return issues
    _validate_string_fields(value, {"id", "content", "impact", "suggestion"}, path, issues)
    _validate_string_array_fields(value, {"affectedTestPointIds"}, path, issues)
    _validate_enum(value, "evidenceStatus", EVIDENCE_STATUSES, path, issues)
    _validate_id(value, "id", "gap", ids, path, issues)
    return issues


def _validate_string_fields(value: dict[str, Any], fields: set[str], path: str, issues: list[ValidationIssue]) -> None:
    for field in fields:
        if not isinstance(value.get(field), str):
            issues.append(ValidationIssue("FIELD_TYPE", f"{field} 必须是字符串", f"{path}.{field}"))
        elif field != "remarks" and not value[field].strip():
            issues.append(ValidationIssue("EMPTY_FIELD", f"{field} 不能为空", f"{path}.{field}"))


def _validate_string_array_fields(value: dict[str, Any], fields: set[str], path: str, issues: list[ValidationIssue]) -> None:
    for field in fields:
        item = value.get(field)
        if not isinstance(item, list) or not all(isinstance(entry, str) for entry in item):
            issues.append(ValidationIssue("FIELD_TYPE", f"{field} 必须是字符串数组", f"{path}.{field}"))


def _validate_enum(value: dict[str, Any], field: str, allowed: set[str], path: str, issues: list[ValidationIssue]) -> None:
    if value.get(field) not in allowed:
        issues.append(ValidationIssue("ENUM_VALUE", f"{field} 不是合法枚举值", f"{path}.{field}"))


def _validate_id(value: dict[str, Any], field: str, kind: str, ids: set[str] | None, path: str, issues: list[ValidationIssue]) -> None:
    item = value.get(field)
    pattern = ID_PATTERNS[kind]
    if not isinstance(item, str) or not pattern.fullmatch(item):
        issues.append(ValidationIssue("ID_FORMAT", f"{field} 格式不正确", f"{path}.{field}"))
        return
    if ids is not None:
        if item in ids:
            issues.append(ValidationIssue("DUPLICATE_ID", f"重复的 {field}: {item}", f"{path}.{field}"))
        ids.add(item)
