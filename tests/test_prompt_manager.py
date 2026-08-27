import unittest

from prompt_manager import PromptTemplateError, render, render_prompt


class TestPromptTemplate(unittest.TestCase):
    def test_render_fills_placeholders(self):
        template = "工作目录：{{workspace}}\n文档：{{requirement_document}}"
        out = render(template, {"workspace": "/data/workspaces/job1", "requirement_document": "# 需求\n正文"})
        self.assertIn("/data/workspaces/job1", out)
        self.assertIn("# 需求\n正文", out)
        self.assertNotIn("{{", out)

    def test_render_missing_variable_raises(self):
        with self.assertRaises(PromptTemplateError):
            render("{{workspace}}", {})

    def test_requirement_analysis_template_renders(self):
        doc = "# 用户登录需求\n1. 输入账号密码登录。\n"
        out = render_prompt(
            "requirement_analysis",
            {
                "workspace": "/data/workspaces/job9",
                "requirement_filename": "需求文档-job9.md",
                "requirement_document": doc,
            },
        )
        self.assertIn(doc, out)
        self.assertIn("/data/workspaces/job9", out)
        self.assertIn("需求文档-job9.md", out)
        self.assertNotIn("{{", out)

    def test_unknown_business_raises(self):
        with self.assertRaises(PromptTemplateError):
            render_prompt("not_exist_business", {})


if __name__ == "__main__":
    unittest.main()