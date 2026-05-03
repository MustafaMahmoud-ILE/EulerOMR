"""Tests for template_compiler module."""
import pytest
from euler_omr.core.template_compiler import TemplateCompiler, LATEX_TEMPLATE
from euler_omr.models.template_model import TemplateConfig


class TestTemplateCompiler:
    def test_find_pdflatex(self):
        result = TemplateCompiler.find_pdflatex()
        # May or may not be installed; just check it doesn't crash
        assert result is None or isinstance(result, str)

    def test_build_latex_source_default(self):
        config = TemplateConfig()
        source = TemplateCompiler.build_latex_source(config)
        assert "\\newcommand{\\IDDigits}{10}" in source
        assert "\\newcommand{\\NumQuestions}{60}" in source
        assert "\\newcommand{\\NumOptions}{4}" in source
        assert "\\newcommand{\\NumVersions}{4}" in source

    def test_build_latex_source_custom(self):
        config = TemplateConfig(
            institution_name="Test Uni",
            id_digits=7,
            num_versions=3,
            num_questions=90,
            num_options=5,
        )
        source = TemplateCompiler.build_latex_source(config)
        assert "Test Uni" in source
        assert "\\newcommand{\\IDDigits}{7}" in source
        assert "\\newcommand{\\NumQuestions}{90}" in source
        assert "\\newcommand{\\NumOptions}{5}" in source
        assert "\\newcommand{\\NumVersions}{3}" in source

    def test_latex_template_is_valid_latex(self):
        assert "\\begin{document}" in LATEX_TEMPLATE
        assert "\\end{document}" in LATEX_TEMPLATE
