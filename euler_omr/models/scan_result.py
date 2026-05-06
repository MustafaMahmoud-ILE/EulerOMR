"""ScanResult dataclass per page: page_no, student_id, version, answers[], state, issues."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class PageState(str, Enum):
    SUCCESS = "SUCCESS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    RESOLVED = "RESOLVED"


class IssueType(str, Enum):
    MISSING_DIGIT = "MISSING_DIGIT"
    MULTI_DIGIT = "MULTI_DIGIT"
    MISSING_VERSION = "MISSING_VERSION"
    MULTI_VERSION = "MULTI_VERSION"
    MISSING_ANSWER = "MISSING_ANSWER"
    MULTI_ANSWER = "MULTI_ANSWER"


@dataclass
class Issue:
    """An issue detected during scan reading."""
    issue_type: IssueType
    field_name: str  # e.g., "id_digit_3", "version", "q_15"
    detail: str = ""
    resolved: bool = False
    resolution: str | None = None

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type.value,
            "field_name": self.field_name,
            "detail": self.detail,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Issue:
        return cls(
            issue_type=IssueType(data["issue_type"]),
            field_name=data["field_name"],
            detail=data.get("detail", ""),
            resolved=data.get("resolved", False),
            resolution=data.get("resolution"),
        )


@dataclass
class ScanResult:
    """Result of scanning a single page."""
    page_no: int
    student_id: str = ""  # May contain '*' for unread digits
    version: str = ""  # e.g., "A", "B", or "" for unread
    answers: list[str] = field(default_factory=list)  # e.g., ["A", "B", "", "C", ...]
    state: PageState = PageState.SUCCESS
    issues: list[Issue] = field(default_factory=list)
    # Crop regions for review dialog (stored as pixel coordinates)
    crop_regions: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "page_no": self.page_no,
            "student_id": self.student_id,
            "version": self.version,
            "answers": self.answers,
            "state": self.state.value,
            "issues": [i.to_dict() for i in self.issues],
            "crop_regions": self.crop_regions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScanResult:
        return cls(
            page_no=data["page_no"],
            student_id=data.get("student_id", ""),
            version=data.get("version", ""),
            answers=data.get("answers", []),
            state=PageState(data.get("state", "SUCCESS")),
            issues=[Issue.from_dict(i) for i in data.get("issues", [])],
            crop_regions=data.get("crop_regions", {}),
        )

    @property
    def unresolved_issues(self) -> list[Issue]:
        return [i for i in self.issues if not i.resolved]

    def update_state(self):
        """Update state based on whether all issues are resolved."""
        if not self.issues:
            self.state = PageState.SUCCESS
        elif all(i.resolved for i in self.issues):
            self.state = PageState.RESOLVED
        else:
            self.state = PageState.NEEDS_REVIEW


@dataclass
class GradeRecord:
    """Grade result for a single student."""
    student_id: str
    version: str
    score: float
    max_score: float
    answers: list[str] = field(default_factory=list)
    percentage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "version": self.version,
            "score": self.score,
            "max_score": self.max_score,
            "answers": self.answers,
            "percentage": self.percentage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GradeRecord:
        return cls(
            student_id=data["student_id"],
            version=data["version"],
            score=data["score"],
            max_score=data["max_score"],
            answers=data.get("answers", []),
            percentage=data.get("percentage", 0.0),
        )
