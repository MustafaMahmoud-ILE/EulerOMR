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
            score = 0.0
            max_score = 0.0
            num_questions = min(active_questions, len(result.answers))
            for q_idx in range(num_questions):
                correct = version_keys.get(q_idx, set())
                weight = answer_key.get_weight(result.version, q_idx)
                max_score += weight
                student = result.answers[q_idx] if q_idx < len(result.answers) else ""
                if student and student in correct:
                    score += weight
            
            pct = (score / max_score * 100) if max_score > 0 else 0.0
            records.append(GradeRecord(
                student_id=result.student_id, version=result.version,
                score=round(score, 2), max_score=round(max_score, 2),
                answers=result.answers[:num_questions], percentage=round(pct, 2),
            ))
            _log(f"Page {result.page_no}: {score:.1f}/{max_score:.1f} ({pct:.1f}%)", "INFO")
        _log(f"Grading complete: {len(records)} students graded", "INFO")
        return records
