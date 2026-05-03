"""ProjectConfig dataclass: template_ref, scans_ref, active settings, answer keys, scan results."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class ProjectConfig:
    """Configuration for an OMR project."""
    active_questions: int = 60
    active_options: int = 4
    active_versions: int = 4

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ProjectConfig:
        return cls(
            active_questions=data.get("active_questions", 60),
            active_options=data.get("active_options", 4),
            active_versions=data.get("active_versions", 4),
        )
