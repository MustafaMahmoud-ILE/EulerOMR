"""Tests for file I/O handlers."""
import pytest
import os
import tempfile
from euler_omr.file_io.eomrt_handler import EomrtHandler
from euler_omr.file_io.eomrp_handler import EomrpHandler
from euler_omr.models.template_model import TemplateConfig
from euler_omr.models.project_model import ProjectConfig
from euler_omr.models.scan_result import ScanResult, PageState
from euler_omr.models.answer_key import AnswerKey


class TestEomrtHandler:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "test.eomrt")
        config = TemplateConfig(institution_name="Test Uni", id_digits=8)
        pdf_bytes = b"fake pdf content"
        EomrtHandler.save(path, config, pdf_bytes, None, None)
        
        loaded = EomrtHandler.load(path)
        assert loaded["config"].institution_name == "Test Uni"
        assert loaded["config"].id_digits == 8
        assert loaded["compiled_pdf_bytes"] == pdf_bytes
        assert loaded["logo_bytes"] is None

    def test_save_with_logo(self, tmp_path):
        path = str(tmp_path / "test.eomrt")
        config = TemplateConfig()
        logo = b"fake logo bytes"
        EomrtHandler.save(path, config, None, logo, "logo.png")
        
        loaded = EomrtHandler.load(path)
        assert loaded["logo_bytes"] == logo
        assert loaded["logo_filename"] == "logo.png"


class TestEomrpHandler:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "test.eomrp")
        config = ProjectConfig(active_questions=30, active_options=4, active_versions=4)
        tc = TemplateConfig()
        ak = AnswerKey()
        ak.set_answer("A", 0, {"A", "B"})
        results = [ScanResult(page_no=1, student_id="123", version="A",
                              answers=["A", "B"], state=PageState.SUCCESS)]
        
        EomrpHandler.save(path, "Test Project", config, tc, None, None, None,
                          None, results, ak, False)
        
        loaded = EomrpHandler.load(path)
        assert loaded["project_name"] == "Test Project"
        assert loaded["config"].active_questions == 30
        assert len(loaded["scan_results"]) == 1
        assert loaded["scan_results"][0].student_id == "123"
        assert "A" in loaded["answer_keys"].get_answer("A", 0)
