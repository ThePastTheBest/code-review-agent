import logging

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
)

from app.core.config import BASE_DIR, settings
from app.models.review import AgentReviewResult
from app.agent.tools import (
    create_review_tools_server,
    set_review_context,
    get_review_result,
    clear_review_context,
)

logger = logging.getLogger(__name__)

TOOL_USAGE_GUIDE = """
## 工具使用指导

你需要通过工具获取信息并完成代码审查。

### 审查流程

1. 首先调用 `get_diff` 工具获取代码差异
2. 如果需要更多上下文来理解变更，调用 `get_file_content` 获取完整文件内容
3. 分析完成后，调用 `submit_review` 提交结构化审查结果

### 重要提示

- 你必须先调用 get_diff 获取差异，再进行分析
- 如果 diff 中某些变更不够清晰，可以用 get_file_content 获取完整文件
- 最终必须调用 submit_review 提交结果，不要只输出文本
"""


class CodeReviewAgent:
    """基于 Claude Agent SDK 的代码审查 Agent"""

    def __init__(self, gitlab_service):
        self.gitlab_service = gitlab_service
        self.model = settings.agent.model
        self.max_turns = settings.agent.max_turns
        self._prompt_template = self._load_prompt_template()
        self._json_schema = self._load_json_schema()

    @staticmethod
    def _load_prompt_template() -> str:
        """从文件加载 prompt 模板"""
        prompt_path = BASE_DIR / "prompt" / "code_review.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _load_json_schema() -> str:
        """加载 JSON Schema"""
        schema_path = BASE_DIR / "prompt" / "code_review_result_json_schema.md"
        with open(schema_path, "r", encoding="utf-8") as f:
            return f.read()

    def _build_system_prompt(self) -> str:
        """构建 system prompt：模板 + json_schema + 工具使用指导"""
        prompt = self._prompt_template.format(json_schema=self._json_schema)
        prompt += "\n" + TOOL_USAGE_GUIDE
        return prompt

    async def review(
        self,
        project: str,
        source_branch: str,
        target_branch: str,
    ) -> AgentReviewResult:
        """执行代码审查（异步多轮 Agent 循环）"""
        # 设置工具上下文
        set_review_context(
            gitlab_service=self.gitlab_service,
            project=project,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        try:
            review_server = create_review_tools_server()

            options = ClaudeAgentOptions(
                system_prompt=self._build_system_prompt(),
                max_turns=self.max_turns,
                mcp_servers={"review": review_server},
                allowed_tools=[
                    "mcp__review__get_diff",
                    "mcp__review__get_file_content",
                    "mcp__review__submit_review",
                ],
            )

            user_prompt = (
                f"请对以下项目进行代码审查：\n"
                f"- 项目: {project}\n"
                f"- 源分支: {source_branch}\n"
                f"- 目标分支: {target_branch}\n\n"
                f"请先调用 get_diff 工具获取代码差异，"
                f"然后进行分析并通过 submit_review 提交结果。"
            )

            logger.info(
                "启动 Agent 审查: project=%s, %s -> %s",
                project,
                source_branch,
                target_branch,
            )

            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_prompt)
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                logger.info("Agent: %s", block.text[:200])

            result = get_review_result()
            if result is None:
                raise RuntimeError(
                    "Agent 未调用 submit_review 提交审查结果"
                )

            logger.info(
                "审查完成: decision=%s, issues=%d",
                result.reviewDecision.value,
                len(result.issues),
            )
            return result

        finally:
            clear_review_context()
