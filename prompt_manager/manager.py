"""提示词模板管理器

职责：根据业务类型从模板库加载对应模板，用上层代码收集好的变量填充占位符，输出最终 Prompt。
模板本身只负责「拿到变量 → 填充占位符 → 输出成品」，不主动获取任何数据。

占位符语法：{{变量名}}
所有占位符都必须由调用方在 variables 中提供，缺失时抛出 PromptTemplateError。
"""

from __future__ import annotations

import re
from pathlib import Path

PROMPT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "prompt_templates"
_PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


class PromptTemplateError(Exception):
    """模板缺失或变量缺失。"""


def load_template(business: str) -> str:
    path = PROMPT_TEMPLATES_DIR / f"{business}.md"
    if not path.is_file():
        raise PromptTemplateError(f"未找到业务提示词模板: {business}（期望路径 {path}）")
    return path.read_text(encoding="utf-8")


def render(template: str, variables: dict) -> str:
    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        if key not in variables:
            raise PromptTemplateError(f"缺少模板变量: {key}")
        return str(variables[key])

    return _PLACEHOLDER.sub(_replace, template)


def render_prompt(business: str, variables: dict) -> str:
    return render(load_template(business), variables)
