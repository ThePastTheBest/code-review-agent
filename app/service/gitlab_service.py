from typing import Optional

import gitlab
from gitlab.v4.objects import Project, ProjectMergeRequest

from app.core.config import settings


class GitLabService:
    """GitLab 操作服务"""

    def __init__(self):
        self.gl = gitlab.Gitlab(
            url=settings.gitlab_env.url,
            private_token=settings.gitlab_env.token,
        )

    def get_project(self, project_path: str) -> Project:
        """获取项目"""
        return self.gl.projects.get(project_path)

    def check_branch_exists(self, project_path: str, branch_name: str) -> bool:
        """检查分支是否存在"""
        try:
            project = self.get_project(project_path)
            project.branches.get(branch_name)
            return True
        except gitlab.exceptions.GitlabGetError:
            return False

    def get_diff(
        self, project_path: str, source_branch: str, target_branch: str
    ) -> str:
        """获取两个分支之间的 diff"""
        project = self.get_project(project_path)
        compare = project.repository_compare(target_branch, source_branch)

        diff_content = []
        for diff in compare.get("diffs", []):
            diff_content.append(f"--- a/{diff['old_path']}")
            diff_content.append(f"+++ b/{diff['new_path']}")
            diff_content.append(diff.get("diff", ""))

        return "\n".join(diff_content)

    def find_or_create_mr(
        self,
        project_path: str,
        source_branch: str,
        target_branch: str,
        title: Optional[str] = None,
    ) -> ProjectMergeRequest:
        """查找或创建 MR"""
        project = self.get_project(project_path)

        # 查找已存在的 MR
        mrs = project.mergerequests.list(
            source_branch=source_branch,
            target_branch=target_branch,
            state="opened",
        )
        if mrs:
            return mrs[0]

        # 创建新的 MR
        mr_title = title or f"Merge {source_branch} into {target_branch}"
        return project.mergerequests.create({
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": mr_title,
        })

    def update_mr_description(
        self, project_path: str, mr_iid: int, description: str
    ) -> None:
        """更新 MR 描述"""
        project = self.get_project(project_path)
        mr = project.mergerequests.get(mr_iid)
        mr.description = description
        mr.save()

    def add_mr_comment(
        self,
        project_path: str,
        mr_iid: int,
        file_path: str,
        line: Optional[int],
        comment: str,
    ) -> None:
        """在 MR 上添加评论"""
        project = self.get_project(project_path)
        mr = project.mergerequests.get(mr_iid)

        if line:
            # 添加行级评论（需要获取 diff 信息）
            try:
                diffs = mr.diffs.list()
                if diffs:
                    latest_diff = diffs[-1]
                    mr.discussions.create({
                        "body": comment,
                        "position": {
                            "base_sha": latest_diff.base_commit_sha,
                            "start_sha": latest_diff.start_commit_sha,
                            "head_sha": latest_diff.head_commit_sha,
                            "position_type": "text",
                            "new_path": file_path,
                            "new_line": line,
                        },
                    })
                    return
            except Exception:
                pass

        # 添加普通评论
        mr.notes.create({"body": f"**{file_path}**\n\n{comment}"})

    def add_mr_general_comment(
        self, project_path: str, mr_iid: int, comment: str
    ) -> None:
        """在 MR 上添加普通评论"""
        project = self.get_project(project_path)
        mr = project.mergerequests.get(mr_iid)
        mr.notes.create({"body": comment})
