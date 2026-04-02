from __future__ import annotations

import ipaddress
from typing import Optional
from urllib.parse import urlparse


def _is_private_host(hostname: str) -> bool:
    h = hostname.strip().lower()
    if h in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return True

    # If it's an IP address, validate it's public.
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_public_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False

    if p.scheme not in {"http", "https"}:
        return False
    if not p.netloc:
        return False
    if not p.hostname:
        return False
    if _is_private_host(p.hostname):
        return False
    return True


def validate_public_http_url(url: str, *, field_name: str) -> Optional[str]:
    if not url:
        return f"{field_name} is empty"
    if not is_public_http_url(url):
        return (
            f"{field_name} must be a PUBLIC http(s) URL reachable by KIE servers "
            f"(got: {url}). If you're testing locally, expose your server via a tunnel "
            f"(ngrok/cloudflared) and set PUBLIC_BASE_URL, or provide an externally hosted image URL."
        )
    return None
