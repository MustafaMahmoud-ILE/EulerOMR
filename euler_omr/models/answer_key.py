"""AnswerKey: version -> question -> set[selected_options]."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class AnswerKey:
    """Answer key mapping: version -> question_index(0-based) -> set of correct option letters.
    Also stores weights: version -> question_index -> float.
    """
    keys: dict[str, dict[int, set[str]]] = field(default_factory=dict)
    weights: dict[str, dict[int, float]] = field(default_factory=dict)

    def set_answer(self, version: str, question_idx: int, options: set[str], weight: float = 1.0):
        if version not in self.keys:
            self.keys[version] = {}
        if version not in self.weights:
            self.weights[version] = {}
        self.keys[version][question_idx] = options
        self.weights[version][question_idx] = weight

    def get_answer(self, version: str, question_idx: int) -> set[str]:
        return self.keys.get(version, {}).get(question_idx, set())

    def get_weight(self, version: str, question_idx: int) -> float:
        return self.weights.get(version, {}).get(question_idx, 1.0)

    def get_version_keys(self, version: str) -> dict[int, set[str]]:
        return self.keys.get(version, {})

    def get_version_weights(self, version: str) -> dict[int, float]:
        return self.weights.get(version, {})

    def to_dict(self) -> dict:
        result = {"keys": {}, "weights": {}}
        for version, questions in self.keys.items():
            result["keys"][version] = {
                str(q_idx): list(options)
                for q_idx, options in questions.items()
            }
        for version, weights in self.weights.items():
            result["weights"][version] = {
                str(q_idx): weight
                for q_idx, weight in weights.items()
            }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> AnswerKey:
        # Support legacy format where data was just the keys dict
        if "keys" not in data:
            keys = {}
            for version, questions in data.items():
                keys[version] = {
                    int(q_idx): set(options)
                    for q_idx, options in questions.items()
                }
            return cls(keys=keys)

        keys = {}
        for version, questions in data.get("keys", {}).items():
            keys[version] = {
                int(q_idx): set(options)
                for q_idx, options in questions.items()
            }
        weights = {}
        for version, w_data in data.get("weights", {}).items():
            weights[version] = {
                int(q_idx): float(weight)
                for q_idx, weight in w_data.items()
            }
        return cls(keys=keys, weights=weights)
