from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # KIE (Nano Banana 2)
    KIE_API_KEY: str = _env("KIE_API_KEY", _env("NANOBANANA_API_KEY", ""))
    KIE_API_BASE: str = _env("KIE_API_BASE", "https://api.kie.ai")
    KIE_FILE_UPLOAD_BASE: str = _env("KIE_FILE_UPLOAD_BASE", "https://kieai.redpandaai.co")

    # If set, will be used to build absolute URLs (uploads + callbacks).
    # Example: https://your-public-domain.com
    PUBLIC_BASE_URL: str = _env("PUBLIC_BASE_URL", "")

    # Uploads
    UPLOADS_DIRNAME: str = _env("UPLOADS_DIRNAME", "uploads")
    MAX_UPLOAD_BYTES: int = _env_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)

    # Debug
    DEBUG_ROUTES: int = _env_int("DEBUG_ROUTES", 0)

    # KIE upload cache (helps speed by reusing already-uploaded tempfile URLs)
    KIE_UPLOAD_CACHE: int = _env_int("KIE_UPLOAD_CACHE", 1)

    # Image proxy (prevents hotlink/CORS issues with third-party images)
    IMAGE_PROXY_ENABLED: int = _env_int("IMAGE_PROXY_ENABLED", 1)
    IMAGE_PROXY_HOSTS: str = _env(
        "IMAGE_PROXY_HOSTS",
        "files.gifts.ru,tempfile.redpandaai.co,tempfile.aiquickdraw.com,tempfile.aiquickdraw.com",
    )
    # Optional external proxy (e.g., Cloudflare Worker) for environments that block outbound requests.
    # Example: https://your-worker.your-subdomain.workers.dev
    EXTERNAL_IMAGE_PROXY_BASE: str = _env("EXTERNAL_IMAGE_PROXY_BASE", "")

    # Make /api/generate return fast (queued job) instead of waiting on upstream.
    GENERATE_ASYNC: int = _env_int("GENERATE_ASYNC", 1)


settings = Settings()
