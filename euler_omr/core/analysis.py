"""Statistical engine: mean, median, mode, stddev; per-version; question-level diagnostics; fairness."""
from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from euler_omr.models.scan_result import GradeRecord
from euler_omr.models.answer_key import AnswerKey
from euler_omr.constants import EASY_THRESHOLD, MODERATE_THRESHOLD, CONFUSION_THRESHOLD, FAIRNESS_THRESHOLD


@dataclass
class QuestionAnalysis:
    question_idx: int
    version: str
    option_frequencies: dict[str, int] = field(default_factory=dict)
    total_responses: int = 0
    correct_count: int = 0
    difficulty_index: float = 0.0
    difficulty_class: str = "MODERATE"
    is_confusing: bool = False


@dataclass
class VersionStats:
    version: str
    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    mode: float = 0.0
    stddev: float = 0.0
    scores: list[float] = field(default_factory=list)


@dataclass
class AnalysisReport:
    overall_mean: float = 0.0
    overall_median: float = 0.0
    overall_mode: float = 0.0
    overall_stddev: float = 0.0
    overall_scores: list[float] = field(default_factory=list)
    version_stats: list[VersionStats] = field(default_factory=list)
    question_analyses: list[QuestionAnalysis] = field(default_factory=list)
    fairness_verdict: str = "FAIR"
    fairness_explanation: str = ""
    version_ranking: list[str] = field(default_factory=list)
    max_score: int = 0


class AnalysisEngine:
    @staticmethod
    def _safe_mode(values):
        try:
            return statistics.mode(values)
        except statistics.StatisticsError:
            return values[0] if values else 0

    @staticmethod
    def _safe_stddev(values):
        return statistics.stdev(values) if len(values) > 1 else 0.0

    @staticmethod
    def analyze(grades: list[GradeRecord], answer_key: AnswerKey, active_questions: int) -> AnalysisReport:
        report = AnalysisReport()
        if not grades:
            return report

        report.max_score = grades[0].max_score if grades else active_questions
        all_scores = [g.score for g in grades]
        report.overall_scores = all_scores
        report.overall_mean = round(statistics.mean(all_scores), 2)
        report.overall_median = round(statistics.median(all_scores), 2)
        report.overall_mode = AnalysisEngine._safe_mode(all_scores)
        report.overall_stddev = round(AnalysisEngine._safe_stddev(all_scores), 2)

        # Per-version stats
        by_version: dict[str, list[GradeRecord]] = {}
        for g in grades:
            by_version.setdefault(g.version, []).append(g)

        for ver, ver_grades in sorted(by_version.items()):
            scores = [g.score for g in ver_grades]
            vs = VersionStats(
                version=ver, count=len(scores),
                mean=round(statistics.mean(scores), 2),
                median=round(statistics.median(scores), 2),
                mode=AnalysisEngine._safe_mode(scores),
                stddev=round(AnalysisEngine._safe_stddev(scores), 2),
                scores=scores,
            )
            report.version_stats.append(vs)

        # Question-level analysis
        for ver, ver_grades in sorted(by_version.items()):
            ver_keys = answer_key.get_version_keys(ver)
            for q_idx in range(active_questions):
                freq: dict[str, int] = {}
                correct_count = 0
                total = 0
                correct_opts = ver_keys.get(q_idx, set())
                for g in ver_grades:
                    ans = g.answers[q_idx] if q_idx < len(g.answers) else ""
                    key = ans if ans else "BLANK"
                    freq[key] = freq.get(key, 0) + 1
                    total += 1
                    if ans in correct_opts:
                        correct_count += 1
                p = correct_count / total if total > 0 else 0
                if p > EASY_THRESHOLD:
                    dc = "EASY"
                elif p >= MODERATE_THRESHOLD:
                    dc = "MODERATE"
                else:
                    dc = "HARD"
                max_freq_ratio = max(freq.values()) / total if total > 0 and freq else 0
                qa = QuestionAnalysis(
                    question_idx=q_idx, version=ver,
                    option_frequencies=freq, total_responses=total,
                    correct_count=correct_count, difficulty_index=round(p, 3),
                    difficulty_class=dc, is_confusing=max_freq_ratio < CONFUSION_THRESHOLD,
                )
                report.question_analyses.append(qa)

        # Fairness
        if len(report.version_stats) >= 2:
            means = [vs.mean for vs in report.version_stats]
            max_mean, min_mean = max(means), min(means)
            ms = report.max_score
            if ms > 0 and (max_mean - min_mean) > FAIRNESS_THRESHOLD * ms:
                report.fairness_verdict = "UNFAIR"
                report.fairness_explanation = (
                    f"Max version mean ({max_mean}) - Min version mean ({min_mean}) "
                    f"= {max_mean - min_mean:.2f}, exceeds {FAIRNESS_THRESHOLD*100:.0f}% of max score ({ms})."
                )
            else:
                report.fairness_verdict = "FAIR"
                report.fairness_explanation = "All version means are within acceptable range."
            ranked = sorted(report.version_stats, key=lambda v: v.mean)
            report.version_ranking = [v.version for v in ranked]

        return report
