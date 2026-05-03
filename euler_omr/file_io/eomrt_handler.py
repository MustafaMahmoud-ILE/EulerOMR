"""Read/write *.eomrt: base64-packed JSON bundle (config + compiled PDF bytes + logo bytes)."""
from __future__ import annotations
import base64, json
from euler_omr.models.template_model import TemplateConfig
from euler_omr.constants import FILE_FORMAT_VERSION


class EomrtHandler:
    @staticmethod
    def save(path: str, config: TemplateConfig, pdf_bytes: bytes | None = None,
             logo_bytes: bytes | None = None, logo_filename: str | None = None):
        data = {
            "version": FILE_FORMAT_VERSION,
            "config": config.to_dict(),
            "compiled_pdf_b64": base64.b64encode(pdf_bytes).decode() if pdf_bytes else None,
            "logo_b64": base64.b64encode(logo_bytes).decode() if logo_bytes else None,
            "logo_filename": logo_filename,
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
        result = {
            "version": data.get("version", "1.0"),
            "config": TemplateConfig.from_dict(data.get("config", {})),
            "compiled_pdf_bytes": base64.b64decode(data["compiled_pdf_b64"]) if data.get("compiled_pdf_b64") else None,
            "logo_bytes": base64.b64decode(data["logo_b64"]) if data.get("logo_b64") else None,
            "logo_filename": data.get("logo_filename"),
        }
        return result
