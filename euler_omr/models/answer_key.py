"""AnswerKey: version -> question -> set[selected_options]."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class AnswerKey:
    """Answer key mapping: version -> question_index(0-based) -> set of correct option letters."""
    keys: dict[str, dict[int, set[str]]] = field(default_factory=dict)

    def set_answer(self, version: str, question_idx: int, options: set[str]):
        if version not in self.keys:
            self.keys[version] = {}
        self.keys[version][question_idx] = options

    def get_answer(self, version: str, question_idx: int) -> set[str]:
        return self.keys.get(version, {}).get(question_idx, set())

    def get_version_keys(self, version: str) -> dict[int, set[str]]:
        return self.keys.get(version, {})

    def to_dict(self) -> dict:
        result = {}
        for version, questions in self.keys.items():
            result[version] = {
                str(q_idx): list(options)
                for q_idx, options in questions.items()
            }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> AnswerKey:
        keys = {}
        for version, questions in data.items():
            keys[version] = {
                int(q_idx): set(options)
                for q_idx, options in questions.items()
            }
        return cls(keys=keys)
