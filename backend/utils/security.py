"""Security helpers that don't belong to a single service."""

from __future__ import annotations

import zipfile
from pathlib import Path


def validate_file_type(file_path: Path, declared_type: str) -> bool:
    """Perform a deterministic content validation independent of HTTP headers.

    This deliberately does not trust a client-supplied Content-Type. It uses
    robust signatures for PDF/DOCX and a UTF-8 decode check for text files.
    """
    try:
        with file_path.open("rb") as f:
            head = f.read(8)
    except OSError:
        return False

    if declared_type == "pdf":
        return head.startswith(b"%PDF-")

    if declared_type == "docx":
        if not head.startswith(b"PK"):
            return False
        try:
            with zipfile.ZipFile(file_path) as archive:
                names = set(archive.namelist())
                return "[Content_Types].xml" in names and "word/document.xml" in names
        except (OSError, zipfile.BadZipFile):
            return False

    if declared_type == "txt":
        try:
            # TextIOWrapper preserves multibyte characters across read boundaries.
            with file_path.open(encoding="utf-8") as f:
                while f.read(64 * 1024):
                    pass
            return True
        except (OSError, UnicodeDecodeError):
            return False

    return False
