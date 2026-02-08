from pathlib import Path

from app.core.config import BASE_DIR, settings


class PromptService:
    """Prompt 管理服务"""

    def __init__(self):
        self.template_path = BASE_DIR / settings.review.prompt_template
        self.schema_path = BASE_DIR / "prompt" / "code_review_result_json_schema.md"

    def load_template(self) -> str:
        """加载 Prompt 模板"""
        with open(self.template_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_json_schema(self) -> str:
        """加载 JSON Schema"""
        with open(self.schema_path, "r", encoding="utf-8") as f:
            return f.read()

    def build_prompt(
        self,
        project: str,
        source_branch: str,
        target_branch: str,
        diff_content: str,
    ) -> str:
        """构建完整的 Prompt"""
        template = self.load_template()
        json_schema = self.load_json_schema()

        return template.format(
            project=project,
            source_branch=source_branch,
            target_branch=target_branch,
            diff_content=diff_content,
            json_schema=json_schema,
        )
