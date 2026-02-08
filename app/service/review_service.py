from app.agent.code_review_agent import CodeReviewAgent
from app.models.review import AgentReviewResult, Severity
from app.service.gitlab_service import GitLabService


class ReviewService:
    """代码审查协调服务"""

    def __init__(self):
        self.gitlab_service = GitLabService()
        self.agent = CodeReviewAgent(gitlab_service=self.gitlab_service)

    async def execute_review(
        self,
        project: str,
        source_branch: str,
        target_branch: str,
    ) -> dict:
        """执行完整的代码审查流程"""
        # 1. Agent 自主获取 diff 并完成审查
        review_result = await self.agent.review(
            project=project,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        # 2. 创建或获取 MR
        mr = self.gitlab_service.find_or_create_mr(
            project, source_branch, target_branch
        )

        # 3. 更新 MR 描述（直接使用 Agent 生成的描述）
        self.gitlab_service.update_mr_description(
            project, mr.iid, review_result.mrDescription
        )

        # 4. 添加问题评论
        self._add_issue_comments(project, mr.iid, review_result)

        return {
            "success": True,
            "message": "代码审查完成",
            "review_result": review_result.model_dump(),
            "mr_url": mr.web_url,
        }

    def _add_issue_comments(
        self, project: str, mr_iid: int, result: AgentReviewResult
    ) -> None:
        """为有问题的代码添加评论"""
        for issue in result.issues:
            if issue.severity in (Severity.HIGH, Severity.CRITICAL, Severity.MEDIUM):
                comment = self._format_issue_comment(issue)
                self.gitlab_service.add_mr_comment(
                    project, mr_iid, issue.file, issue.line, comment
                )

    @staticmethod
    def _format_issue_comment(issue) -> str:
        """格式化问题评论"""
        return f"""**[{issue.severity.value.upper()}] {issue.category.value}**

{issue.description}

**建议**: {issue.suggestion}"""
