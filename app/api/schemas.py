from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.review import (
    AgentReviewResult,
    Category,
    Issue,
    ReviewDecision,
    Severity,
)


class ReviewRequest(BaseModel):
    """代码审查请求"""
    project: str
    source_branch: str
    target_branch: str


class ReviewResponse(BaseModel):
    """代码审查响应"""
    success: bool
    message: str
    review_result: Optional[Dict[str, Any]] = None
    mr_url: Optional[str] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str = "1.0.0"
