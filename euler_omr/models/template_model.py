"""TemplateConfig dataclass: institution_name, logo_path, id_digits, num_versions, num_questions, num_options."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class TemplateConfig:
    """Configuration for an OMR template."""
    institution_name: str = "University"
    logo_path: str | None = None
    id_digits: int = 10
    num_versions: int = 4
    num_questions: int = 60
    num_options: int = 4

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TemplateConfig:
        return cls(
            institution_name=data.get("institution_name", "University"),
            logo_path=data.get("logo_path"),
            id_digits=data.get("id_digits", 10),
            num_versions=data.get("num_versions", 4),
            num_questions=data.get("num_questions", 60),
            num_options=data.get("num_options", 4),
        )
