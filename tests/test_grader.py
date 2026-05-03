"""Tests for grader module."""
import pytest
from euler_omr.core.grader import Grader
from euler_omr.models.scan_result import ScanResult, PageState
from euler_omr.models.answer_key import AnswerKey


class TestGrader:
    def _make_answer_key(self):
        ak = AnswerKey()
        for q in range(5):
            ak.set_answer("A", q, {"A"})
        return ak

    def test_grade_perfect(self):
        ak = self._make_answer_key()
        results = [ScanResult(
            page_no=1, student_id="1234567890", version="A",
            answers=["A", "A", "A", "A", "A"],
            state=PageState.SUCCESS,
        )]
        grades = Grader.grade(results, ak, 5)
        assert len(grades) == 1
        assert grades[0].score == 5
        assert grades[0].percentage == 100.0

    def test_grade_partial(self):
        ak = self._make_answer_key()
        results = [ScanResult(
            page_no=1, student_id="1234567890", version="A",
            answers=["A", "B", "A", "C", "A"],
            state=PageState.SUCCESS,
        )]
        grades = Grader.grade(results, ak, 5)
        assert grades[0].score == 3

    def test_skip_needs_review(self):
        ak = self._make_answer_key()
        results = [ScanResult(
            page_no=1, student_id="123", version="A",
            answers=["A"] * 5,
            state=PageState.NEEDS_REVIEW,
        )]
        grades = Grader.grade(results, ak, 5)
        assert len(grades) == 0

    def test_grade_blank_answers(self):
        ak = self._make_answer_key()
        results = [ScanResult(
            page_no=1, student_id="123", version="A",
            answers=["", "", "", "", ""],
            state=PageState.SUCCESS,
        )]
        grades = Grader.grade(results, ak, 5)
        assert grades[0].score == 0
