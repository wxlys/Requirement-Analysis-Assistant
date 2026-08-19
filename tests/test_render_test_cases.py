from __future__ import annotations

import unittest

from test_case_generation.render_test_cases import render


class RenderTestCasesTests(unittest.TestCase):
    def test_render_contains_case_details(self):
        document = {
            "testCases": [
                {
                    "id": "UC-001",
                    "testPointIds": ["TP-LOGIN-001"],
                    "requirementIds": ["REQ-LOGIN-001"],
                    "requirementSources": [{"section": "第4节", "summary": "合法登录"}],
                    "category": "正向",
                    "name": "合法账号密码登录成功",
                    "preconditions": ["用户已注册"],
                    "testData": ["合法账号"],
                    "steps": ["提交登录请求"],
                    "expectedResults": ["HTTP 200"],
                    "postconditions": ["记录审计"],
                    "priority": "P0",
                    "status": "可执行",
                    "assumptionIds": [],
                }
            ]
        }
        markdown = render(document)
        self.assertIn("## UC-001 合法账号密码登录成功", markdown)
        self.assertIn("类别：正向 | 优先级：P0 | 状态：可执行", markdown)
        self.assertIn("**预期结果：**\n1. HTTP 200", markdown)
        self.assertIn("用例总数：1", markdown)

    def test_render_escapes_newlines(self):
        document = {
            "testCases": [
                {
                    "id": "UC-001",
                    "testPointIds": [],
                    "requirementIds": [],
                    "requirementSources": [{"section": "第1节", "summary": "多行\n摘要"}],
                    "category": "正向",
                    "name": "多行摘要",
                    "preconditions": [],
                    "testData": [],
                    "steps": [],
                    "expectedResults": [],
                    "postconditions": [],
                    "priority": "P0",
                    "status": "可执行",
                    "assumptionIds": [],
                }
            ]
        }
        markdown = render(document)
        self.assertIn("多行<br>摘要", markdown)
        self.assertIn("**前置条件：** 无", markdown)


if __name__ == "__main__":
    unittest.main()