"""Read/write *.eomrp: base64-packed JSON bundle (project config + template + scans + results + keys)."""
from __future__ import annotations
import base64, json
from euler_omr.models.project_model import ProjectConfig
from euler_omr.models.template_model import TemplateConfig
from euler_omr.models.scan_result import ScanResult
from euler_omr.models.answer_key import AnswerKey
from euler_omr.constants import FILE_FORMAT_VERSION


class EomrpHandler:
    @staticmethod
    def save(path: str, project_name: str, config: ProjectConfig,
             template_config: TemplateConfig, template_pdf_bytes: bytes | None,
             template_logo_bytes: bytes | None, template_logo_filename: str | None,
             scans_pdf_bytes: bytes | None, scan_results: list[ScanResult],
             answer_keys: AnswerKey, chk_run_analysis: bool):
        data = {
            "version": FILE_FORMAT_VERSION,
            "project_name": project_name,
            "config": config.to_dict(),
            "template": {
                "version": FILE_FORMAT_VERSION,
                "config": template_config.to_dict(),
                "compiled_pdf_b64": base64.b64encode(template_pdf_bytes).decode() if template_pdf_bytes else None,
                "logo_b64": base64.b64encode(template_logo_bytes).decode() if template_logo_bytes else None,
                "logo_filename": template_logo_filename,
            },
            "scans_pdf_b64": base64.b64encode(scans_pdf_bytes).decode() if scans_pdf_bytes else None,
            "scan_results": [r.to_dict() for r in scan_results],
            "answer_keys": answer_keys.to_dict(),
            "chk_run_analysis": chk_run_analysis,
        }
        encoded = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
        with open(path, "w", encoding="utf-8") as f:
            f.write(encoded)

    @staticmethod
    def load(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            encoded = f.read()
        raw = base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
        data = json.loads(raw)
        tmpl = data.get("template", {})
        return {
            "version": data.get("version", "1.0"),
            "project_name": data.get("project_name", "Untitled"),
            "config": ProjectConfig.from_dict(data.get("config", {})),
            "template_config": TemplateConfig.from_dict(tmpl.get("config", {})),
            "template_pdf_bytes": base64.b64decode(tmpl["compiled_pdf_b64"]) if tmpl.get("compiled_pdf_b64") else None,
            "template_logo_bytes": base64.b64decode(tmpl["logo_b64"]) if tmpl.get("logo_b64") else None,
            "template_logo_filename": tmpl.get("logo_filename"),
            "scans_pdf_bytes": base64.b64decode(data["scans_pdf_b64"]) if data.get("scans_pdf_b64") else None,
            "scan_results": [ScanResult.from_dict(r) for r in data.get("scan_results", [])],
            "answer_keys": AnswerKey.from_dict(data.get("answer_keys", {})),
            "chk_run_analysis": data.get("chk_run_analysis", False),
        }
