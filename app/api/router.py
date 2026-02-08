import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    ErrorResponse,
    HealthResponse,
    ReviewRequest,
    ReviewResponse,
)
from app.service.gitlab_service import GitLabService
from app.service.review_service import ReviewService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(status="healthy")


@router.post(
    "/review",
    response_model=ReviewResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def create_review(request: ReviewRequest):
    """创建代码审查"""
    gitlab_service = GitLabService()

    # 校验项目
    try:
        gitlab_service.get_project(request.project)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"项目不存在或无权访问: {request.project}",
        )

    # 校验源分支
    if not gitlab_service.check_branch_exists(request.project, request.source_branch):
        raise HTTPException(
            status_code=400,
            detail=f"源分支不存在: {request.source_branch}",
        )

    # 校验目标分支
    if not gitlab_service.check_branch_exists(request.project, request.target_branch):
        raise HTTPException(
            status_code=400,
            detail=f"目标分支不存在: {request.target_branch}",
        )

    # 执行代码审查
    try:
        review_service = ReviewService()
        result = await review_service.execute_review(
            project=request.project,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
        )
        return ReviewResponse(**result)
    except Exception as e:
        logger.exception("代码审查失败")
        raise HTTPException(
            status_code=500,
            detail=f"代码审查失败: {str(e)}",
        )
