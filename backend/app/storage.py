from __future__ import annotations

import secrets
from pathlib import Path
from typing import Final, Tuple

from fastapi import HTTPException, Request, UploadFile

from .config import settings


ALLOWED_IMAGE_CONTENT_TYPES: Final[set[str]] = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}

ALLOWED_IMAGE_EXTS: Final[set[str]] = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def uploads_dir() -> Path:
    directory = repo_root() / settings.UPLOADS_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_ext(filename: str, content_type: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".png"):
        return ".png"
    if name.endswith(".jpeg"):
        return ".jpg"
    if name.endswith(".jpg") or name.endswith(".jpeg"):
        return ".jpg"
    if name.endswith(".webp"):
        return ".webp"
    if name.endswith(".gif"):
        return ".gif"
    if content_type == "image/png":
        return ".png"
    if content_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if content_type == "image/webp":
        return ".webp"
    if content_type == "image/gif":
        return ".gif"
    return ".bin"


def _public_base_url(request: Request) -> str:
    if settings.PUBLIC_BASE_URL.strip():
        return settings.PUBLIC_BASE_URL.rstrip("/")
    return str(request.base_url).rstrip("/")


def build_file_url(request: Request, relative_path: str) -> str:
    base = _public_base_url(request)
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path
    return base + relative_path


def _is_allowed_image(file: UploadFile) -> bool:
    filename = (file.filename or "").lower()
    suffix = Path(filename).suffix
    if suffix in ALLOWED_IMAGE_EXTS:
        return True

    ct = (file.content_type or "").lower()
    if ct in ALLOWED_IMAGE_CONTENT_TYPES:
        return True

    # Some clients send application/octet-stream for images.
    if ct in {"application/octet-stream", "binary/octet-stream"} and suffix in ALLOWED_IMAGE_EXTS:
        return True

    return False


async def save_upload_image(request: Request, file: UploadFile) -> Tuple[str, str]:
    if not _is_allowed_image(file):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type (content-type={file.content_type}, filename={file.filename})",
        )

    blob = await file.read()
    if len(blob) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    ext = _safe_ext(file.filename or "", file.content_type or "")
    filename = f"{secrets.token_hex(16)}{ext}"
    path = uploads_dir() / filename
    path.write_bytes(blob)

    url = build_file_url(request, f"/uploads/{filename}")
    return filename, url
