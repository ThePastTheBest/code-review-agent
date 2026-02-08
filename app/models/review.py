from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STABILITY = "stability"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_COMMENTS = "approve-with-comments"
    REQUEST_CHANGES = "request-changes"

    @property
    def label(self) -> str:
        return _DECISION_LABELS[self]


_DECISION_LABELS = {
    ReviewDecision.APPROVE: "通过",
    ReviewDecision.APPROVE_WITH_COMMENTS: "有条件通过",
    ReviewDecision.REQUEST_CHANGES: "需要修改",
}


class Issue(BaseModel):
    severity: Severity
    category: Category
    file: str
    line: Optional[int] = None
    description: str
    suggestion: str


class AgentReviewResult(BaseModel):
    """Agent 返回的审查结果"""

    mrDescription: str
    issues: List[Issue]
    reviewDecision: ReviewDecision
