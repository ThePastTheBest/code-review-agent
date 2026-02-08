import json
import logging
from typing import Any, Dict, Optional

from claude_agent_sdk import tool, create_sdk_mcp_server

from app.models.review import AgentReviewResult

logger = logging.getLogger(__name__)

# 模块级上下文，用于在工具间共享状态
_review_context: Dict[str, Any] = {}


def set_review_context(
    gitlab_service: Any,
    project: str,
    source_branch: str,
    target_branch: str,
) -> None:
    """设置审查上下文，供工具函数使用"""
    _review_context.update({
        "gitlab_service": gitlab_service,
        "project": project,
        "source_branch": source_branch,
        "target_branch": target_branch,
        "review_result": None,
    })


def get_review_result() -> Optional[AgentReviewResult]:
    """获取 Agent 提交的审查结果"""
    return _review_context.get("review_result")


def clear_review_context() -> None:
    """清理审查上下文"""
    _review_context.clear()


@tool(
    "get_diff",
    "获取两个分支之间的代码差异(diff)。在开始代码审查前必须先调用此工具。",
    {
        "project": str,
        "source_branch": str,
        "target_branch": str,
    },
)
async def get_diff(args: dict) -> dict:
    """获取分支间的代码差异"""
    gitlab_service = _review_context.get("gitlab_service")
    if not gitlab_service:
        return {
            "content": [{"type": "text", "text": "错误: 审查上下文未初始化"}],
            "isError": True,
        }

    try:
        diff = gitlab_service.get_diff(
            args["project"], args["source_branch"], args["target_branch"]
        )
        if not diff.strip():
            return {
                "content": [{"type": "text", "text": "两个分支之间没有代码差异。"}]
            }
        logger.info("成功获取 diff，长度: %d", len(diff))
        return {"content": [{"type": "text", "text": diff}]}
    except Exception as e:
        logger.exception("获取 diff 失败")
        return {
            "content": [{"type": "text", "text": f"获取 diff 失败: {e}"}],
            "isError": True,
        }


@tool(
    "get_file_content",
    "获取指定分支上某个文件的完整内容。当你需要更多上下文来理解代码变更时使用此工具。",
    {
        "project": str,
        "file_path": str,
        "branch": str,
    },
)
async def get_file_content(args: dict) -> dict:
    """获取文件完整内容"""
    gitlab_service = _review_context.get("gitlab_service")
    if not gitlab_service:
        return {
            "content": [{"type": "text", "text": "错误: 审查上下文未初始化"}],
            "isError": True,
        }

    try:
        project = gitlab_service.get_project(args["project"])
        file_content = project.files.get(
            file_path=args["file_path"], ref=args["branch"]
        )
        content = file_content.decode().decode("utf-8")
        logger.info(
            "成功获取文件内容: %s (分支: %s)",
            args["file_path"],
            args["branch"],
        )
        return {"content": [{"type": "text", "text": content}]}
    except Exception as e:
        logger.exception("获取文件内容失败")
        return {
            "content": [
                {"type": "text", "text": f"获取文件内容失败: {e}"}
            ],
            "isError": True,
        }


@tool(
    "submit_review",
    "提交代码审查的结构化结果。审查完成后必须调用此工具提交最终结果。"
    "参数 review_json 必须是严格符合 JSON Schema 的字符串。",
    {
        "review_json": str,
    },
)
async def submit_review(args: dict) -> dict:
    """提交结构化审查结果"""
    review_json_str = args.get("review_json", "")

    try:
        review_data = json.loads(review_json_str)
    except json.JSONDecodeError as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"JSON 格式错误: {e}。请修正后重新提交。",
                }
            ],
            "isError": True,
        }

    try:
        result = AgentReviewResult.model_validate(review_data)
        _review_context["review_result"] = result
        logger.info("审查结果已提交: decision=%s", result.reviewDecision.value)
        return {
            "content": [
                {"type": "text", "text": "审查结果已成功提交。"}
            ]
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"审查结果校验失败: {e}。请按照 JSON Schema 修正后重新提交。",
                }
            ],
            "isError": True,
        }


def create_review_tools_server():
    """创建包含所有审查工具的 SDK MCP Server"""
    return create_sdk_mcp_server(
        name="review-tools",
        version="1.0.0",
        tools=[get_diff, get_file_content, submit_review],
    )
