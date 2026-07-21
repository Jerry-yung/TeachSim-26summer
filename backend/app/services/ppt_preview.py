from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def convert_office_to_pdf(source_path: Path) -> Path | None:
    """Try converting office file to PDF via LibreOffice/soffice."""
    source = Path(source_path).resolve()
    if not source.exists():
        return None

    source_suffix = source.suffix.lower()
    if source_suffix == ".pdf":
        return source
    if source_suffix not in {".ppt", ".pptx"}:
        return None

    out_dir = source.parent
    converted = out_dir / f"{source.stem}.pdf"
    for bin_name in ("soffice", "libreoffice"):
        binary = shutil.which(bin_name)
        if not binary:
            continue
        try:
            subprocess.run(
                [
                    binary,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(out_dir),
                    str(source),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if converted.exists():
                return converted
        except Exception:
            continue
    return None
