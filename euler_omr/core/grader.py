"""Answer-key application; score computation per student per version."""
from __future__ import annotations
import structlog
from euler_omr.models.scan_result import ScanResult, PageState, GradeRecord
from euler_omr.models.answer_key import AnswerKey

logger = structlog.get_logger(__name__)


class Grader:
    @staticmethod
    def grade(scan_results, answer_key, active_questions, log_callback=None):
        _log = log_callback or (lambda msg, level: None)
        records = []
        for result in scan_results:
            if result.state == PageState.NEEDS_REVIEW:
                _log(f"Page {result.page_no}: Skipping — unresolved issues", "WARNING")
                continue
            if not result.version:
                _log(f"Page {result.page_no}: Skipping — no version", "WARNING")
                continue
            version_keys = answer_key.get_version_keys(result.version)
            if not version_keys:
                _log(f"Page {result.page_no}: Skipping — no key for {result.version}", "WARNING")
                continue
            score = 0
            max_score = min(active_questions, len(result.answers))
            for q_idx in range(max_score):
                correct = version_keys.get(q_idx, set())
                student = result.answers[q_idx] if q_idx < len(result.answers) else ""
                if student and student in correct:
                    score += 1
            pct = (score / max_score * 100) if max_score > 0 else 0.0
            records.append(GradeRecord(
                student_id=result.student_id, version=result.version,
                score=score, max_score=max_score,
                answers=result.answers[:max_score], percentage=round(pct, 2),
            ))
            _log(f"Page {result.page_no}: {score}/{max_score} ({pct:.1f}%)", "INFO")
        _log(f"Grading complete: {len(records)} students graded", "INFO")
        return records
