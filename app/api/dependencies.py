from fastapi import Depends, HTTPException

from app.service.gitlab_service import GitLabService


def get_gitlab_service() -> GitLabService:
    """获取 GitLab 服务实例"""
    return GitLabService()


def validate_gitlab_params(
    project: str,
    source_branch: str,
    target_branch: str,
    gitlab_service: GitLabService = Depends(get_gitlab_service),
) -> dict:
    """校验 GitLab 参数"""
    # 检查项目是否存在
    try:
        gitlab_service.get_project(project)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"项目不存在或无权访问: {project}",
        )

    # 检查源分支是否存在
    if not gitlab_service.check_branch_exists(project, source_branch):
        raise HTTPException(
            status_code=400,
            detail=f"源分支不存在: {source_branch}",
        )

    # 检查目标分支是否存在
    if not gitlab_service.check_branch_exists(project, target_branch):
        raise HTTPException(
            status_code=400,
            detail=f"目标分支不存在: {target_branch}",
        )

    return {
        "project": project,
        "source_branch": source_branch,
        "target_branch": target_branch,
    }
