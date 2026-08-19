from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from analysis_quality_gate.pipeline import process, validate_document


def point(**overrides):
    value = {
        "id": "TP-LOGIN-001",
        "requirementId": "REQ-LOGIN-001",
        "sourceSection": "第4节",
        "sourceSummary": "合法账号和密码可以成功登录",
        "module": "用户登录",
        "type": "正向",
        "name": "合法账号密码登录成功",
        "priority": "P0",
        "preconditions": ["用户已注册且状态正常"],
        "testData": ["合法账号", "正确密码"],
        "trigger": "提交登录请求",
        "expected": ["HTTP 200", "返回认证凭证", "创建有效会话"],
        "postconditions": ["记录成功登录事件"],
        "evidenceStatus": "原文明确",
        "status": "可直接生成用例",
        "gapIds": [],
        "remarks": "",
    }
    value.update(overrides)
    return value


def gap(**overrides):
    value = {
        "id": "GAP-001",
        "content": "账号格式未定义",
        "affectedTestPointIds": ["TP-LOGIN-002"],
        "impact": "无法构造非法账号格式数据",
        "suggestion": "明确账号格式",
        "evidenceStatus": "需求缺失",
    }
    value.update(overrides)
    return value


class QualityGateTests(unittest.TestCase):
    def test_valid_document_passes(self):
        pending = point(
            id="TP-LOGIN-002",
            requirementId="REQ-LOGIN-002",
            name="非法账号格式被拒绝",
            type="反向",
            priority="P1",
            status="待补充需求",
            gapIds=["GAP-001"],
            expected=["请求被拒绝"],
        )
        result = validate_document({"testPoints": [point(), pending], "gaps": [gap()]})
        self.assertTrue(result["passed"], result)

    def test_missing_required_field_fails_structure(self):
        invalid = point()
        del invalid["expected"]
        result = validate_document({"testPoints": [invalid], "gaps": []})
        self.assertFalse(result["passed"])
        self.assertEqual(result["stage"], "structure")
        self.assertTrue(any(item["code"] == "MISSING_FIELD" for item in result["errors"]))

    def test_gap_status_conflict_fails_business_validation(self):
        invalid = point(gapIds=["GAP-001"])
        result = validate_document({"testPoints": [invalid], "gaps": [gap(affectedTestPointIds=["TP-LOGIN-001"])]})
        self.assertFalse(result["passed"])
        self.assertEqual(result["stage"], "business")
        self.assertTrue(any(item["code"] == "STATUS_GAP_CONFLICT" for item in result["errors"]))

    def test_uncertain_expected_fails_business_validation(self):
        invalid = point(expected=["请求被拒绝或重定向"])
        result = validate_document({"testPoints": [invalid], "gaps": []})
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["code"] == "UNCERTAIN_EXPECTED" for item in result["errors"]))

    def test_merged_input_fields_fail_business_validation(self):
        invalid = point(
            type="反向",
            name="多个字段类型非法",
            testData=["`account`、`password`、`rememberMe`类型非法"],
            expected=["请求被拒绝"],
        )
        result = validate_document({"testPoints": [invalid], "gaps": []})
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["code"] == "MERGED_INPUT_FIELDS" for item in result["errors"]))

    def test_process_only_writes_formal_result_after_validation(self):
        document = {"testPoints": [point()], "gaps": []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "analysis.json"
            input_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            output_dir = root / "output"
            self.assertEqual(process(input_path, output_dir), 0)
            self.assertTrue((output_dir / "validated" / "analysis.json").exists())
            self.assertTrue((output_dir / "需求分析结果.md").exists())

    def test_process_rejects_invalid_result(self):
        document = {"testPoints": [point(gapIds=["GAP-001"])], "gaps": [gap(affectedTestPointIds=["TP-LOGIN-001"])]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "analysis.json"
            input_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            output_dir = root / "output"
            self.assertEqual(process(input_path, output_dir), 1)
            self.assertFalse((output_dir / "validated" / "analysis.json").exists())
            self.assertFalse((output_dir / "需求分析结果.md").exists())
            self.assertTrue((output_dir / "reports" / "validation.json").exists())


if __name__ == "__main__":
    unittest.main()
