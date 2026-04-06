from __future__ import annotations

import secrets
from pathlib import Path
from typing import Final, Tuple
from urllib.parse import urlparse

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
    explicit = settings.PUBLIC_BASE_URL.strip().rstrip("/")
    request_base = str(request.base_url).rstrip("/")
    if not explicit:
        return request_base

    # If we are behind a proxy/https and the request already carries the correct
    # public origin (via Host + X-Forwarded-Proto), prefer it to avoid mixed-content
    # issues when PUBLIC_BASE_URL is stale (e.g., still pointing to an http:// IP).
    try:
        parsed_req = urlparse(request_base)
        parsed_explicit = urlparse(explicit)
    except Exception:
        return explicit

    req_host = (parsed_req.hostname or "").strip().lower()
    if parsed_req.scheme == "https" and req_host and req_host not in {"localhost", "127.0.0.1", "0.0.0.0"}:
        explicit_host = (parsed_explicit.hostname or "").strip().lower()
        if parsed_explicit.scheme != "https":
            return request_base
        if explicit_host and explicit_host != req_host:
            return request_base

    return explicit


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


async def save_upload_image(request: Request, file: UploadFile, remove_bg: bool = False) -> Tuple[str, str, str]:
    if not _is_allowed_image(file):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type (content-type={file.content_type}, filename={file.filename})",
        )

    blob = await file.read()
    if len(blob) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    upload_filename = file.filename or "file"
    upload_content_type = file.content_type or ""

    # NOTE: `remove_bg` is kept for backward compatibility with older clients.
    # Background removal is now handled at generation time via the model prompt.
    _ = bool(remove_bg)

    ext = _safe_ext(upload_filename, upload_content_type)
    filename = f"{secrets.token_hex(16)}{ext}"
    path = uploads_dir() / filename
    path.write_bytes(blob)

    url = build_file_url(request, f"/uploads/{filename}")
    return filename, url, upload_content_type
